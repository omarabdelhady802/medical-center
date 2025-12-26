import requests
import logging
from agent_builder.medical_agent import MedicalAgent
from agent_builder.repositories import ClinicRepository

logger = logging.getLogger(__name__)


class FacebookHandler:
    """
    Facebook Messenger Handler (Stateless – Production Ready)

    - No in-memory agent cache
    - Each request builds a fresh MedicalAgent
    - Memory is handled بالكامل من DB
    """

    def __init__(self, page_access_token, fireworks_key):
        self.access_token = page_access_token
        self.fireworks_api_key = fireworks_key
        self.api_url = "https://graph.facebook.com/v17.0/me/messages"

    def handle_event(self, messaging_event, page_id):
        """
        Handle a single messaging event from Facebook webhook
        """
        sender_id = None
        try:
            # 1️⃣ تأكد إن ده message
            if "message" not in messaging_event:
                return

            message_data = messaging_event.get("message", {})

            # 2️⃣ تجاهل echo
            if message_data.get("is_echo"):
                return

            # 3️⃣ Parse incoming message
            sender_id, msg_type, content = self._parse_incoming(messaging_event)
            if not sender_id:
                return

            # =========================
            # 💬 TEXT MESSAGE → AI
            # =========================
            if msg_type == "text" and content:
                clinic = ClinicRepository.get_by_page_id(page_id)
                if not clinic:
                    self.send_message(
                        sender_id,
                        "⚠️ العيادة غير متاحة حالياً، حاول لاحقاً"
                    )
                    return

                agent = MedicalAgent(
                    platform_id=1,
                    clinic_id=clinic.id,
                    page_id=page_id,
                    sender_id=sender_id,
                    api_key=self.fireworks_api_key
                )

                reply = agent.chat(content)
                self.send_message(sender_id, reply)

            # =========================
            # 📎 ATTACHMENTS
            # =========================
            elif msg_type in ["voice", "image", "pdf"]:
                responses = {
                    "voice": "🎤 وصلتني رسالتك الصوتية، هراجعها وأرد عليك",
                    "image": "📸 وصلتني الصورة، شكراً ليك",
                    "pdf": "📄 تم استلام ملف الـ PDF"
                }
                self.send_message(
                    sender_id,
                    responses.get(msg_type, "تم استلام المرفق بنجاح")
                )

            # =========================
            # ❓ UNKNOWN
            # =========================
            else:
                self.send_message(
                    sender_id,
                    "ℹ️ تم استلام رسالتك، وسيتم مراجعتها"
                )

        except Exception as e:
            logger.exception("Error handling Facebook message")
            if sender_id:
                self.send_message(
                    sender_id,
                    "❌ حصل خطأ أثناء معالجة رسالتك"
                )

    def _parse_incoming(self, messaging_event):
        """
        Parse incoming event from Facebook and return:
        (sender_id, message_type, content)
        """
        sender_id = messaging_event["sender"]["id"]
        message_data = messaging_event.get("message", {})

        # 📎 Attachments
        if "attachments" in message_data:
            att = message_data["attachments"][0]
            att_type = att.get("type")
            url = att.get("payload", {}).get("url")

            if att_type == "audio":
                return sender_id, "voice", url

            if att_type == "file" and url and ".pdf" in url.lower():
                return sender_id, "pdf", url

            return sender_id, att_type, url

        # 💬 Text
        if "text" in message_data:
            return sender_id, "text", message_data["text"]

        return sender_id, "unknown", None

    def send_message(self, recipient_id, text):
        """
        Send a text message to Facebook Messenger
        """
        if not text:
            return

        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }

        try:
            r = requests.post(
                self.api_url,
                json=payload,
                params={"access_token": self.access_token},
                timeout=20
            )
            r.raise_for_status()
            logger.info(f"Message sent to {recipient_id}")
        except requests.RequestException as e:
            logger.error(
                f"Failed to send message to {recipient_id}: {e}"
            )
