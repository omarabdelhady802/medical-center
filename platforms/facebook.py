import requests
from agent_builder.medical_agent import medical_agent
from agent_builder.repositories import ClinicRepository

class FacebookHandler:
    def __init__(self, page_access_token, fireworks_key):
        self.access_token = page_access_token
        self.fireworks_api_key = fireworks_key
        self.api_url = "https://graph.facebook.com/v17.0/me/messages"

    def handle_event(self, messaging_event, page_id):
        # 1. التأكد إن الحدث هو "رسالة" فعلاً (مش إشعار قراءة أو وصول)
        if 'message' not in messaging_event:
            return 

        message_data = messaging_event.get('message', {})
        
        # 2. حماية الـ Echo (لو البوت هو اللي باعت)
        if message_data.get('is_echo'):
            print("🤫 Ignoring echo message (bot's own reply)")
            return
        
        # 3. استخراج البيانات
        sender_id, msg_type, content = self._parse_incoming(messaging_event)
        
        # 4. جلب العيادة من الداتابيز
        clinic = ClinicRepository.get_by_page_id(page_id)
        if not clinic:
            print(f"⚠️ No clinic for page_id: {page_id}")
            return

        # 5. معالجة الرسالة بناءً على نوعها
        if msg_type == "text":
            agent = medical_agent(
                platform_id=1,
                clinic_id=clinic.id,
                page_id=page_id,
                sender_id=sender_id,
                api_key=self.fireworks_api_key
            )
            reply = agent.chat(content)
            self.send_message(sender_id, reply)
        
        elif msg_type in ["voice", "image", "pdf"]:
            responses = {
                "voice": "وصلتني رسالتك الصوتية وجاري سماعها.. 🎤",
                "image": "شكراً على الصورة، سيتم مراجعتها.. 📸",
                "pdf": "تم استلام ملف الـ PDF.. 📄"
            }
            self.send_message(sender_id, responses.get(msg_type, "تم استلام المرفق."))

    def _parse_incoming(self, messaging_event):
        sender_id = messaging_event['sender']['id']
        message_data = messaging_event.get('message', {})
        
        # فحص المرفقات
        if 'attachments' in message_data:
            att = message_data['attachments'][0]
            url = att['payload'].get('url')
            if att['type'] == 'file' and url and '.pdf' in url.lower():
                return sender_id, "pdf", url
            return sender_id, att['type'], url
            
        # فحص النص
        if 'text' in message_data:
            return sender_id, "text", message_data['text']
            
        return sender_id, "unknown", None

    def send_message(self, recipient_id, text):
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        try:
            r = requests.post(self.api_url, json=payload, params={"access_token": self.access_token})
            r.raise_for_status() # عشان لو فيه Error يطلعلك في الـ Terminal
        except Exception as e:
            print(f"❌ Failed to send message: {e}")