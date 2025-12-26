import os
import requests
import logging
from agent_builder.medical_agent import MedicalAgent
from agent_builder.repositories import ClinicRepository, ClientRepository

logger = logging.getLogger(__name__)

class WAHAHandler:
    """
    WAHA (WhatsApp API) Handler Production-ready.
    Supports multiple instances/pages dynamically and integrates with MedicalAgent.
    """

    def __init__(self, api_url, instance, api_key):
        self.api_url = api_url
        self.instance = instance
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json", "X-Api-Key": self.api_key}
        self.agents = {}  # cache لكل client/page

    def get_agent(self, page_id, sender_id):
        """
        Fetch or create a MedicalAgent dynamically for a given page + sender
        """
        clinic = ClinicRepository.get_by_page_id(page_id)
        if not clinic:
            logger.error(f"No clinic found for page_id: {page_id}")
            return None

        client = ClientRepository.get_or_create(
            platform_id="waha",
            clinic_id=clinic.id,
            page_id=page_id,
            sender_id=sender_id
        )

        key = (page_id, sender_id)
        if key not in self.agents:
            self.agents[key] = MedicalAgent(
                platform_id="waha",
                clinic_id=clinic.id,
                page_id=page_id,
                sender_id=sender_id,
                api_key=self.api_key
            )
        return self.agents[key]

    def handle_payload(self, payload):
        """
        Handle incoming WAHA webhook payload
        """
        try:
            # تجاهل رسائل المجموعات
            if "participant" in payload:
                logger.info("Message from group, ignoring...")
                return None

            chat_id = payload.get("from")
            if not chat_id:
                logger.warning("No chat_id in payload")
                return None

            body = payload.get("body", "")
            has_media = payload.get("hasMedia", False)
            media = payload.get("media", {})

            # الميديا
            if has_media and media:
                reply = self.parse_media(media)
                return self.send_message(chat_id, reply)

            # نصوص
            if body:
                # نجيب page_id من الـ payload أو DB حسب الـ chat_id
                page_id = payload.get("page_id", "default_page")  # replace logic as needed
                agent = self.get_agent(page_id, chat_id)
                if not agent:
                    return self.send_message(chat_id, "⚠️ لا يمكن معالجة رسالتك حالياً.")

                reply = agent.chat(body)
                return self.send_message(chat_id, reply)

            # fallback
            return self.send_message(chat_id, "ℹ️ تم استلام رسالتك")

        except Exception as e:
            logger.error(f"Failed to handle message from {payload.get('from')}: {e}")
            self.send_message(payload.get("from"), "❌ حدث خطأ أثناء معالجة رسالتك")

    def parse_media(self, media):
        mimetype = media.get("mimetype", "")
        filename = media.get("filename", "file")
        if mimetype == "image/webp":
            return "😀 I received a sticker!"
        elif mimetype.startswith("image/"):
            return "📷 I received an image"
        elif mimetype.startswith("video/"):
            return "🎥 I received a video"
        elif mimetype.startswith("audio/"):
            return "🎵 I received an audio"
        elif mimetype == "application/pdf":
            return f"🧾 I received a PDF document: {filename}"
        else:
            return f"📎 I received a file of type: {mimetype}"

    def send_message(self, chat_id, text):
        data = {"session": self.instance, "chatId": chat_id, "text": text}
        try:
            r = requests.post(f"{self.api_url}/api/sendText", json=data, headers=self.headers, timeout=5)
            r.raise_for_status()
            logger.info(f"Message sent to {chat_id}")
            return r.json()
        except requests.RequestException as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return {"status": "error", "error": str(e)}
