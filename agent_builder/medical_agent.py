from datetime import datetime, timedelta
import logging
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from .repositories import ClinicRepository, ClientRepository
from .services import MemoryService
from .tools import book_appointment, check_numofexmantions
from .prompt import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger(__name__)

TOOL_MAP = {
    "book_appointment": book_appointment,
    "check_numofexmantions": check_numofexmantions,
}

# 1. تعريف الـ Schema لضمان دقة الـ JSON وتجنب الـ Hallucination
class ChatResponse(BaseModel):
    reply: str = Field(description="الرد النصي الموجه للمستخدم باللغة العربية")
    summary: str = Field(description="ملخص المحادثة المحدث والبيانات المستخرجة")

class MedicalAgent:
    def __init__(self, platform_id, clinic_id, page_id, sender_id, api_key=None):
        load_dotenv()
        
        # الجزء الخاص بالبيانات (زي ما هو)
        self.client_data = ClientRepository.get_or_create(
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

        # إعداد الـ LLM (استخدام النسخة الأحدث والأكثر استقراراً)
        key = os.getenv("GEMINI_KEY")
        if not key:
            raise ValueError("Google Gemini API key is required")

        llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest", # تم التحديث لأفضل نسخة تدعم Structured Output
            google_api_key=key
        )

        # ربط الأدوات (Tools)
        self.llm_with_tools = llm.bind_tools([book_appointment, check_numofexmantions])
        
        # ربط الـ Structured Output للمحادثات العادية
        self.structured_llm = llm.with_structured_output(ChatResponse)

    def _get_history_summary(self):
        now = datetime.now()
        two_weeks_ago = now - timedelta(days=14)
        expiration = self.client_data.expiration_date

        if expiration and expiration < two_weeks_ago:
            return "the chat history has expired."
        return self.client_data.chat_summary or "No previous history."

    def chat(self, message: str):
        chat_summary = self._get_history_summary()
        full_system_prompt = SYSTEM_PROMPT.format(**self.context)

        messages = [
            SystemMessage(content=full_system_prompt),
            HumanMessage(content=USER_PROMPT.format(
                summary=chat_summary,
                last_reply=self.client_data.last_bot_reply or "",
                message=message
            ))
        ]

        try:
            # أولاً: بننادي الـ LLM مع الأدوات عشان نشوف لو عايز يحجز أو يستعلم
            response = self.llm_with_tools.invoke(messages)
            
            # --- مراقبة التكلفة في كل رسالة ---
            usage = getattr(response, "usage_metadata", None)
            if usage:
                print(f"\n📊 TOKENS USAGE | Input: {usage.get('input_tokens')} | Output: {usage.get('output_tokens')} | Total: {usage.get('total_tokens')}")

            reply = ""
            new_summary = self.client_data.chat_summary or ""

            # الحالة الأولى: الـ LLM قرر يستخدم Tool
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                func = TOOL_MAP.get(tool_name)
                result = func.invoke(tool_args) if func else None

                if tool_name == "book_appointment":
                    reply = result.get("message", "❌ حدث خطأ غير متوقع.")
                    if result.get("status") == "success":
                        new_summary = (self.client_data.chat_summary or "") + \
                            f" | Action: Booking SUCCESS - {result.get('service_name')} on {result.get('appointment_date')}"

                elif tool_name == "check_numofexmantions":
                    reply = result.get("message", "❌ حدث خطأ أثناء التحقق.")
                    label = result.get("label", "")
                    patient_id = result.get("patient_id", tool_args.get("patient_id", ""))
                    if label == "consultation_success":
                        new_summary = (self.client_data.chat_summary or "") + \
                            f" | Action: Consultation SUCCESS - patient_id={patient_id} remaining={result.get('remaining')}"
                    elif label == "patient_not_found":
                        new_summary = (self.client_data.chat_summary or "") + \
                            f" | Action: Consultation FAILED - patient_id={patient_id} not found"
                    elif label == "balance_exhausted":
                        new_summary = (self.client_data.chat_summary or "") + \
                            f" | Action: Consultation FAILED - patient_id={patient_id} balance exhausted"

            # الحالة الثانية: محادثة عادية (نجبره يرجع Structured Output)
            else:
                structured_response = self.structured_llm.invoke(messages)
                reply = structured_response.reply
                new_summary = structured_response.summary

            # تحديث الذاكرة (Memory)
            MemoryService.update(
                client=self.client_data,
                summary=new_summary,
                last_reply=reply
            )

            return reply

        except Exception as e:
            logger.error(f"Error in Agent Chat: {e}")
            return "عذراً، واجهت مشكلة تقنية. حاول لاحقاً."