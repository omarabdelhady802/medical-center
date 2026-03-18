from datetime import datetime, timedelta
import logging
import os
import re
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from .repositories import ClinicRepository, ClientRepository
from .services import MemoryService
from .tools import book_appointment, check_numofexmantions
from .prompt import SYSTEM_PROMPT
from models.models import RequestCounter

logger = logging.getLogger(__name__)

TOOL_MAP = {
    "book_appointment": book_appointment,
    "check_numofexmantions": check_numofexmantions,
}
SUMMARY_TEMPLATES = {
    "booking_success": "Action: BOOKING SUCCESS | Name: {patient_name} | Service: {service_name} | Date: {appointment_date} | Phone: {phone_number}",
    "booking_failed": "Action: BOOKING FAILED | Attempted for {patient_name}",
    "consultation_success": "Action: SUCCESS | Consultation deducted for ID {patient_id}. Left: {remaining}",
    "balance_exhausted": "Action: FAILED | Patient {patient_id} has 0 balance.",
    "patient_not_found": "Action: FAILED | Patient ID {patient_id} not found.",
    "technical_error": "Action: ERROR | Server issue for ID {patient_id}."
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
        return self.client_data.chat_summary or "No previous history."

    def chat(self, message: str):
        chat_summary = self._get_history_summary()
        full_system_prompt = SYSTEM_PROMPT.format(**self.context)

        messages = [
            SystemMessage(content=full_system_prompt),
            HumanMessage(content=f"Summary: {chat_summary}\nLast Reply: {self.client_data.last_bot_reply}\nUser: {message}")
        ]

        try:
            # أولاً: بننادي الـ LLM مع الأدوات عشان نشوف لو عايز يحجز أو يستعلم
            counter = RequestCounter.query.first()
            if counter:
                counter.decrement()
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

                if isinstance(result, dict):
                    reply = result.get("message", "تمت معالجة طلبك.")

                    # 2. تحديث الـ Summary باستخدام الـ Templates
                    label = result.get("label")
                    template = SUMMARY_TEMPLATES.get(label)
                    
                    if template:
                        try:
                            # دمج البيانات في القالب المخصص للـ label
                            log_entry = template.format(**result)
                            new_summary = (self.client_data.chat_summary or "") + f" | {log_entry}"
                        except Exception as e:
                            logger.error(f"Format Error: {e}")
                else:
                    reply = result if isinstance(result, str) else "❌ حدث خطأ فني."

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