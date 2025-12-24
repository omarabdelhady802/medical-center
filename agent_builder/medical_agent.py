from langchain_fireworks import ChatFireworks
from langchain_core.prompts import ChatPromptTemplate

from .repositories import ClinicRepository, ClientRepository
from .services import MemoryService
from .tools import create_booking_tool
from .prompt import SYSTEM_PROMPT, USER_PROMPT, SUMMARY_PROMPT


class medical_agent:
    def __init__(self, platform_id, clinic_id, page_id, sender_id, api_key):

        # 1️⃣ Client (memory owner)
        self.client = ClientRepository.get_or_create(
            platform_id, clinic_id, page_id, sender_id
        )

        # 2️⃣ Clinic context
        clinic = ClinicRepository.get_by_page_id(page_id)

        if not clinic:
            raise ValueError("Clinic not found")

        self.context = {
            "clinic_name": clinic.name,
            "clinic_type": "Heart Center",
            "address": clinic.address or "",
            "services": clinic.services or "No services listed",
            "subservices": clinic.subservices or ""
        }

        # 3️⃣ Main LLM
        self.llm = ChatFireworks(
            model="accounts/fireworks/models/kimi-k2-instruct-0905",
            temperature=0,
            api_key=api_key
        )

        # 4️⃣ Booking tool
        self.booking_tool = create_booking_tool(self.client)
        # ربط الـ Tool بالـ LLM بشكل صحيح
        self.llm = self.llm.bind_tools([self.booking_tool])

        # 5️⃣ Summary LLM
        self.summary_llm = ChatFireworks(
            model="accounts/fireworks/models/kimi-k2-instruct-0905",
            temperature=0,
            api_key=api_key
        )

        # 6️⃣ Prompts
        self.main_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT)
        ])

        self.summary_prompt = ChatPromptTemplate.from_template(
            SUMMARY_PROMPT
        )

    def chat(self, message: str):
        # 1️⃣ Generate response
        messages = self.main_prompt.format_messages(
            message=message,
            summary=self.client.chat_summary or "",
            last_reply=self.client.last_bot_reply or "",
            **self.context
        )

        response = self.llm.invoke(messages)

        # 2️⃣ Tool handling
        # بنفترض إن الرد هو كلام الـ AI العادي
        reply = response.content 

        if response.tool_calls:
            for call in response.tool_calls:
                if call["name"] == self.booking_tool.name:
                    # تنفيذ الأداة (تأكد إن دي بتنادي الحجز فعلاً)
                    self.booking_tool.invoke(call["args"])
                    reply = "تم الحجز بنجاح ✅ (تم تسجيل بياناتك في ملف الإكسيل)"
                    break 

        # 3️⃣ Summarization
        summary_messages = self.summary_prompt.format_messages(
            summary=self.client.chat_summary or "",
            user_message=message,
            bot_reply=reply
        )

        summary_response = self.summary_llm.invoke(summary_messages)
        new_summary = summary_response.content

        # 4️⃣ Save memory
        MemoryService.update(
            client=self.client,
            summary=new_summary,
            last_reply=reply
        )

        return reply