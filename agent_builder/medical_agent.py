import json
import logging
import os
from dotenv import load_dotenv
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
        
        load_dotenv()
        FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")

        # 2. إعداد الموديل
        self.llm = ChatFireworks(
            model="accounts/fireworks/models/kimi-k2-instruct-0905",
            temperature=0,
            api_key=FIREWORKS_API_KEY,
        )

        # 3. إعداد الأدوات
        self.booking_tool = create_booking_tool()
        self.llm_with_tools = self.llm.bind_tools([self.booking_tool])

        # 4. إعداد الـ Prompts
        self.main_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT)
        ])

    def chat(self, message: str):
        """
        معالجة الرسائل النصية والتحقق من استدعاء الأدوات
        """
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

        # --- المسار الأول: إذا قرر الموديل استخدام أداة الحجز (Tool Calling) ---
        if hasattr(response, "tool_calls") and response.tool_calls:
            print(f"[DEBUG] Tool Call Detected: {response.tool_calls[0]['name']}")
            for tool_call in response.tool_calls:
                if tool_call.get("name") == "book_appointment":
                    args = tool_call.get("args", {})
                    # تنفيذ الحجز فعلياً
                    result = self.booking_tool.invoke(args)
                    
                    if isinstance(result, dict) and result.get("status") == "success":
                        reply = f"✅ تم تأكيد حجزك بنجاح يا {args.get('patient_name', 'فندم')}!\n📍 الموعد: {args.get('appointment_date')}\n🏥 الخدمة: {args.get('service_name')}\n\nننتظرك في العيادة."
                        new_summary = f"{new_summary} | [Action: Booked {args.get('service_name')}]"
                    else:
                        reply = "❌ عذراً، واجهت مشكلة في تسجيل الحجز. سأقوم بإبلاغ موظف الاستقبال فوراً ليتواصل معك."
                    break
            
            # تحديث الذاكرة والرد فوراً
            MemoryService.update(client=self.client, summary=new_summary, last_reply=reply)
            return reply

        # --- المسار الثاني: رد نصي عادي أو تحليل JSON مدمج ---
        content = response.content.strip()
        
        # لو الموديل بعت JSON كـ نص بدلاً من Tool Call (Fallback)
        if '"patient_name"' in content and '"appointment_date"' in content:
             reply = "تمام، هل تؤكد حجزك بهذه البيانات؟" # رد بسيط لتجنب إظهار الـ JSON
        else:
            try:
                # تنظيف الـ Markdown لو الموديل بعته كـ JSON
                json_str = content
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                
                data = json.loads(json_str)
                reply = data.get("reply", content)
                new_summary = data.get("new_summary", new_summary)
                
            except Exception as e:
                logger.warning(f"JSON Parsing failed, using raw response: {e}")
                reply = content

        # تحديث الذاكرة
        MemoryService.update(
            client=self.client,
            summary=new_summary,
            last_reply=reply
        )

        return reply