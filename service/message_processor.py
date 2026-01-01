from models.models import ClinicPage


class IncomingMessage:
    def __init__(self, sender_id, msg_type, text=None, media=None):
        self.sender_id = sender_id
        self.type = msg_type
        self.text = text
        self.media = media


def process_message(handler_cls, platform_id, page_id, message):
    """
    معالج الرسائل الرئيسي
    
    يجلب بيانات الصفحة من DB
    ينشئ Handler مناسب
    يعالج الرسالة
    يرسل الرد
    """
    clinic_page = ClinicPage.query.filter_by(
        platform_id=platform_id,
        page_id=str(page_id)
    ).first()

    if not clinic_page:
        print(f"[WARNING] No clinic page found for platform {platform_id}, page {page_id}")
        return

    try:
        handler = handler_cls(clinic_page)
        reply = handler.handle(message)
        
        if reply:
            handler.send(message.sender_id, reply)
    
    except Exception as e:
        print(f"[ERROR] process_message failed: {e}")
        import traceback
        traceback.print_exc()