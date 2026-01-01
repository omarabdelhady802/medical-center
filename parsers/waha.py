from service.message_processor import IncomingMessage


def parse_waha_message(payload):
    """
    تحليل رسائل WhatsApp (WAHA) وتحويلها لـ IncomingMessage
    
    Args:
        payload: WAHA webhook payload
        
    Returns:
        IncomingMessage object أو None
    """
    sender_id = payload.get("from")
    if not sender_id:
        return None

    has_media = payload.get("hasMedia", False)
    media = payload.get("media")

    # ===== معالجة الميديا (صور، فيديو، صوت، ملفات) =====
    if has_media and media:
        mimetype = media.get("mimetype", "")
        
        # تحديد نوع الملف بناءً على mimetype
        if "image/webp" in mimetype:
            msg_type = "sticker"  # ملصقات واتساب
        elif "image/" in mimetype:
            msg_type = "image"
        elif "video/" in mimetype:
            msg_type = "video"
        elif "audio/" in mimetype or "ptt" in payload.get("type", ""):
            # ptt = Push To Talk (رسائل صوتية)
            msg_type = "voice"
        elif "application/pdf" in mimetype:
            msg_type = "document"  # PDF
        else:
            msg_type = "file"  # أي ملف آخر

        return IncomingMessage(
            sender_id=sender_id,
            msg_type=msg_type,
            text=payload.get("body"),  # النص المرفق مع الميديا (إن وجد)
            media=media  # نبعت media object كامل
        )

    # ===== معالجة الرسائل النصية =====
    if payload.get("body"):
        return IncomingMessage(
            sender_id=sender_id,
            msg_type="text",
            text=payload.get("body")
        )

    # لو مفيش نص ولا ميديا
    return None