import json
import logging
from langchain_fireworks import ChatFireworks
from langchain_core.prompts import ChatPromptTemplate
from .repositories import ClinicRepository, ClientRepository
from .services import MemoryService
from .tools import create_booking_tool
from .prompt import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger(__name__)

class MedicalAgent:
    def __init__(self, platform_id, clinic_id, page_id, sender_id, api_key):
        # 1. تهيئة العميل والعيادة
        self.client = ClientRepository.get_or_create(platform_id, clinic_id, page_id, sender_id)
        clinic = ClinicRepository.get_by_page_id(page_id)
        if not clinic: 
            raise ValueError("Clinic not found")

        self.context = {
            "clinic_name": clinic.name,
            "address": clinic.address or "",
            "services": clinic.services or "No services listed",
            "subservices": clinic.subservices or ""
        }

        # 2. إعداد الموديل (بدون فرض JSON Mode تقنياً لمنع التعارض مع الـ Tools)
        self.llm = ChatFireworks(
            model="accounts/fireworks/models/kimi-k2-instruct-0905",
            temperature=0,
            api_key=api_key
        )

        # 3. إعداد الأدوات
        self.booking_tool = create_booking_tool() # لا يحتاج لباراميتر الآن
        self.llm_with_tools = self.llm.bind_tools([self.booking_tool])

        # 4. إعداد الـ Prompts
        self.main_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT)
        ])

    def chat(self, message: str):
        # تحضير الرسائل للموديل
        messages = self.main_prompt.format_messages(
            message=message,
            summary=self.client.chat_summary or "No history.",
            last_reply=self.client.last_bot_reply or "",
            **self.context
        )

        # استدعاء الموديل
        response = self.llm_with_tools.invoke(messages)
        
        reply = ""
        new_summary = self.client.chat_summary or ""

        # --- المسار الأول: إذا قرر الموديل استخدام أداة الحجز (Tool Call) ---
        tool_calls = getattr(response, "tool_calls", [])
        if tool_calls:
            for call in tool_calls:
                if call.get("name") == "book_appointment":
                    # تنفيذ الحجز الفعلي في الإكسيل
                    result = self.booking_tool.invoke(call.get("args", {}))
                    
                    # التحقق من نجاح الحجز
                    if isinstance(result, dict) and result.get("status") == "success":
                        reply = "تم تأكيد حجزك بنجاح ✅"
                        new_summary = f"{new_summary} | [Action: Booked {call.get('args', {}).get('service_name')} on {call.get('args', {}).get('appointment_date')}]"
                    else:
                        reply = "عذراً، حدث خطأ أثناء الحجز، يرجى تزويدي بالبيانات مرة أخرى ❌"
                        new_summary = f"{new_summary} | [Action: Booking Failed]"
                    break
            
            # تحديث الذاكرة فوراً بعد استخدام الأداة
            MemoryService.update(client=self.client, summary=new_summary, last_reply=reply)
            return reply

        # --- المسار الثاني: رد نصي عادي (يجب أن يكون بتنسيق JSON حسب الـ System Prompt) ---
        try:
            content = response.content.strip()
            # تنظيف الـ Markdown من الرد إذا وجد
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            reply = data.get("reply", "")
            new_summary = data.get("new_summary", new_summary)
            
        except Exception as e:
            # Fallback في حالة رد الموديل بنص خام (ليس JSON)
            logger.warning(f"JSON Parsing failed, using raw response: {e}")
            reply = response.content
            new_summary = f"{new_summary}\n- User: {message}\n- Bot: {reply}"

        # تحديث قاعدة البيانات بالملخص والرد الجديد
        MemoryService.update(
            client=self.client,
            summary=new_summary,
            last_reply=reply
        )

        return reply