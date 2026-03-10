from datetime import datetime, timedelta
import json
import logging
import os
from dotenv import load_dotenv

# --- Gemini Imports ---
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .repositories import ClinicRepository, ClientRepository
from .services import MemoryService
from .tools import create_booking_tool
from .prompt import SYSTEM_PROMPT, USER_PROMPT
from notified_center.EmailSender import EmailClient

logger = logging.getLogger(__name__)
email_client = EmailClient()

class MedicalAgent:
    def __init__(self, platform_id, clinic_id, page_id, sender_id, api_key=None):
        self.client = ClientRepository.get_or_create( 
            platform_id, clinic_id, page_id, sender_id
        )

        clinic = ClinicRepository.get_by_page_id(page_id)
        if not clinic:
            raise ValueError("Clinic not found")

        self.context = {
            "clinic_name": clinic.name,
            "address": clinic.address or "",
            "services": clinic.services or "No services listed",
            "subservices": clinic.subservices or ""
        }

        load_dotenv()
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

        self.llm = ChatOpenAI(
           model="google/gemini-2.0-flash-001", # تقدر تختار أي موديل من OpenRouter
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0,
        )

        self.booking_tool = create_booking_tool()
        
        # ربط الأدوات بـ Gemini
        self.llm_with_tools = self.llm.bind_tools([self.booking_tool])

        self.main_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT)
        ])

    def chat(self, message: str):
        now = datetime.now()
        two_weeks_ago = now - timedelta(days=14)
        expiration_date = self.client.expiration_date

        if expiration_date is None:
            chat_summary = self.client.chat_summary or ""
        elif expiration_date < two_weeks_ago:
            chat_summary = "the chat history has expired."
        else:
            chat_summary = self.client.chat_summary or ""

        messages = self.main_prompt.format_messages(
            message=message,
            summary=chat_summary,
            last_reply=self.client.last_bot_reply or "",
            **self.context
        )

        # --- Gemini Call ---
        response = self.llm_with_tools.invoke(messages)

        reply = ""
        new_summary = self.client.chat_summary or ""

        # --- 4️⃣ Tool Calling path ---
        if response.tool_calls:
            print(f"[DEBUG] Gemini Tool Call Detected: {response.tool_calls[0]['name']}")

            for tool_call in response.tool_calls:
                if tool_call.get("name") == "book_appointment":
                    args = tool_call.get("args", {})
                    result = self.booking_tool.invoke(args)

                    if isinstance(result, dict) and result.get("status") == "success":
                        reply = (
                            f"✅ تم تأكيد حجزك بنجاح يا {args.get('patient_name', 'فندم')}!\n"
                            f"📍 الموعد: {args.get('appointment_date')}\n"
                            f"🏥 الخدمة: {args.get('service_name')}\n\n"
                            "ننتظرك في العيادة."
                        )
                        new_summary += f" | [Action: Booked {args.get('service_name')}]"
                    else:
                        reply = (
                            "❌ عذراً، واجهت مشكلة في تسجيل الحجز.\n"
                            "سيقوم موظف الاستقبال بالتواصل معك قريباً."
                        )
                    break

            MemoryService.update(
                client=self.client,
                summary=new_summary,
                last_reply=reply
            )
            return reply

        # -----------------------------
        # 5️⃣ Normal text / JSON fallback
        # -----------------------------
        
        # حماية ضد خطأ AttributeError: 'list' object has no attribute 'strip'
        if isinstance(response.content, list):
            content = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in response.content])
        else:
            content = str(response.content or "")

        content = content.strip()

        if not content.startswith("{") and not content.startswith("```"):
            reply = content
        else:
            try:
                json_str = content
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()

                data = json.loads(json_str)
                reply = data.get("reply", content)
                new_summary = data.get("new_summary", new_summary)

            except Exception as e:
                logger.warning(f"JSON Parsing failed, using raw text: {e}")
                reply = content

        # -----------------------------
        # 6️⃣ Save memory & return
        # -----------------------------
        MemoryService.update(
            client=self.client,
            summary=new_summary,
            last_reply=reply
        )

        return reply