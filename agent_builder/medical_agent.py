from datetime import datetime
import logging
import os
import json
import time
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from .repositories import ClinicRepository, ClientRepository
from .services import MemoryService
from .tools import book_appointment, check_numofexmantions
from .prompt import SYSTEM_PROMPT, USER_PROMPT
from models.models import RequestCounter

logger = logging.getLogger(__name__)

TOOL_MAP = {
    "book_appointment": book_appointment,
    # "check_numofexmantions": check_numofexmantions,
}


class ChatResponse(BaseModel):
    reply: str
    summary: Optional[str] = ""


def clean_json_response(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1]
        if content.startswith("json"):
            content = content[4:]
    return content.strip()


def safe_merge_summary(old_summary: str, new_summary: str) -> str:
    if not new_summary:
        return old_summary or ""
    return new_summary


class MedicalAgent:
    def __init__(self, platform_id, clinic_id, page_id, sender_id, api_key=None):
        load_dotenv()

        self.client_data = ClientRepository.get_or_create(
            platform_id, clinic_id, page_id, sender_id
        )

        clinic = ClinicRepository.get_by_page_id(page_id)
        if not clinic:
            raise ValueError("Clinic not found")

        self.context = {
            "clinic_name": clinic.name,
            "address": clinic.address or "",
            "services": clinic.services or "",
            "subservices": clinic.subservices or ""
        }

        key = os.getenv("GEMINI_KEY")
        if not key:
            raise ValueError("Google Gemini API key is required")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=key,
            temperature=0.2,
        )

        self.llm = llm.bind_tools(
            [book_appointment],
            tool_choice="auto"
        )

    def _get_history_summary(self):
        return self.client_data.chat_summary or ""

    def chat(self, message: str):
        total_start = time.time()

        chat_summary = self._get_history_summary()

        messages = [
            SystemMessage(content=SYSTEM_PROMPT.format(**self.context)),
            HumanMessage(content=USER_PROMPT.format(
                summary=chat_summary,
                last_reply=self.client_data.last_bot_reply or "",
                message=message,
                **self.context
            ))
        ]

        try:
            # Rate limiting
            counter = RequestCounter.query.first()
            if counter:
                counter.decrement()

            # LLM CALL
            llm_start = time.time()
            response = self.llm.invoke(messages)
            llm_end = time.time()
            print(f"🧠 LLM Time: {llm_end - llm_start:.2f}s")

            usage = getattr(response, "usage_metadata", None)
            if usage:
                print(f"📊 TOKENS | Input: {usage.get('input_tokens')} | Output: {usage.get('output_tokens')}")

            reply = ""
            new_summary = self.client_data.chat_summary or ""

            # ===============================
            # 🛠️ TOOL CALL
            # ===============================
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                func = TOOL_MAP.get(tool_name)

                tool_start = time.time()
                result = func.invoke(tool_args) if func else None
                tool_end = time.time()
                print(f"🛠️ Tool ({tool_name}) Time: {tool_end - tool_start:.2f}s")

                if tool_name == "book_appointment":
                    reply = result.get("message", "❌ حدث خطأ غير متوقع.")
                    if result.get("status") == "success":
                        new_summary += f" | Booking SUCCESS: {result.get('service_name')} on {result.get('appointment_date')}"

                """            
                 elif tool_name == "check_numofexmantions":
                    reply = result.get("message", "❌ حدث خطأ أثناء التحقق.")
                    label = result.get("label", "")
                    patient_id = result.get("patient_id", tool_args.get("patient_id", ""))

                    if label == "consultation_success":
                        from models.models import db, Platform, ClinicBranch, save_for_exmnation
                        platform = Platform.query.get(self.client_data.platform_id)
                        clinic = ClinicBranch.query.get(self.client_data.clinic_id)
                        record = save_for_exmnation(
                            platform_name=platform.name if platform else str(self.client_data.platform_id),
                            clinic_name=clinic.name if clinic else str(self.client_data.clinic_id),
                            patient_id=patient_id,
                        )
                        db.session.add(record)
                        db.session.commit()
                        new_summary += f" | Consultation SUCCESS: patient_id={patient_id} remaining={result.get('remaining')}"

                    elif label == "patient_not_found":
                        new_summary += f" | Consultation FAILED: patient_id={patient_id} not found"

                    elif label == "balance_exhausted":
                        new_summary += f" | Consultation FAILED: patient_id={patient_id} balance exhausted"
                    """
            # ===============================
            # 💬 NORMAL RESPONSE (JSON)
            # ===============================
            else:
                try:
                    content = response.content

                    if isinstance(content, list):
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        content = "\n".join(text_parts)

                    content = clean_json_response(content)
                    parsed = json.loads(content)

                    if isinstance(parsed, list):
                        parsed = parsed[0]

                    validated = ChatResponse(**parsed)
                    reply = validated.reply

                    new_summary = safe_merge_summary(
                        old_summary=self.client_data.chat_summary or "",
                        new_summary=validated.summary
                    )

                except Exception as e:
                    print("⚠️ Parsing Error:", e)
                    print("RAW RESPONSE:", response.content)
                    reply = "عذراً، حدث خطأ في معالجة الرد."
                    new_summary = self.client_data.chat_summary or ""

            # ===============================
            # 💾 MEMORY UPDATE
            # ===============================
            mem_start = time.time()
            MemoryService.update(
                client=self.client_data,
                summary=new_summary,
                last_reply=reply
            )
            mem_end = time.time()
            print(f"💾 Memory Time: {mem_end - mem_start:.2f}s")

            total_end = time.time()
            print(f"🚀 TOTAL TIME: {total_end - total_start:.2f}s")
            print("=" * 50)

            return reply

        except Exception as e:
            logger.error(f"Error in Agent Chat: {e}")
            return "عذراً، واجهت مشكلة تقنية. حاول لاحقاً."