from service.message_processor import IncomingMessage


def parse_facebook_message(event):
    """
    تحليل رسائل Facebook Messenger وتحويلها لـ IncomingMessage
    
    Args:
        event: Facebook webhook event
        
    Returns:
        IncomingMessage object أو None
    """
    msg = event.get("message")
    
    # تجاهل الرسائل المرتدة (echo) من البوت نفسه
    if not msg or msg.get("is_echo"):
        return None

    sender_id = event["sender"]["id"]

    # ===== معالجة Attachments (صور، ملفات، فيديوهات، إلخ) =====
    if "attachments" in msg:
        att = msg["attachments"][0]  # نأخذ أول attachment
        att_type = att.get("type")   # image, file, video, audio
        payload = att.get("payload", {})
        
        # تحويل "file" إلى "document" للتوافق مع نظام OCR
        if att_type == "file":
            # فحص إذا كان الملف PDF
            mime_type = payload.get("mime_type", "").lower()
            url = payload.get("url", "").lower()
            
            # لو PDF، نغير النوع لـ "document"
            if "pdf" in mime_type or ".pdf" in url:
                att_type = "document"
        
        return IncomingMessage(
            sender_id=sender_id,
            msg_type=att_type,
            media=payload  # نبعت الـ payload كامل (فيه الـ URL)
        )

    # ===== معالجة النصوص =====
    if "text" in msg:
        return IncomingMessage(
            sender_id=sender_id,
            msg_type="text",
            text=msg["text"]
        )

    # لو مفيش text ولا attachments
    return None