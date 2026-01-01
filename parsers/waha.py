import logging
import traceback
from service.message_processor import IncomingMessage
from notified_center.EmailSender import EmailClient

logger = logging.getLogger(__name__)
emailclient = EmailClient()

def parse_waha_message(payload):
    """
    تحليل رسائل WhatsApp (WAHA) مع معالجة الأخطاء والتنبيه عبر الإيميل
    """
    try:
        # 1. التحقق الأساسي من الـ Payload
        if not isinstance(payload, dict):
            return None

        # 2. استخراج ID المرسل مع حماية وتنبيه
        sender_id = payload.get("from")
        if not sender_id:
            logger.warning("WAHA payload received without 'from' field")
            emailclient.send_email(
                subject="Missing Sender ID in WhatsApp Message (WAHA Parser)",
                body=f"A WAHA message payload was received without a sender ID:\n\n{payload}"
            )
            return None

        has_media = payload.get("hasMedia", False)
        media = payload.get("media")
        msg_body = payload.get("body")

        # 3. معالجة الميديا (صور، فيديو، صوت، ملفات)
        if has_media and media:
            try:
                mimetype = media.get("mimetype", "")
                payload_type = payload.get("type", "")
                
                # تحديد نوع الملف بناءً على mimetype
                if "image/webp" in mimetype:
                    msg_type = "sticker"
                elif "image/" in mimetype:
                    msg_type = "image"
                elif "video/" in mimetype:
                    msg_type = "video"
                elif "audio/" in mimetype or "ptt" in payload_type:
                    msg_type = "voice"
                elif "application/pdf" in mimetype:
                    msg_type = "document"
                else:
                    msg_type = "file"

                return IncomingMessage(
                    sender_id=sender_id,
                    msg_type=msg_type,
                    text=msg_body,
                    media=media
                )
            except Exception as media_err:
                error_msg = f"Error parsing WAHA media: {str(media_err)}\n{traceback.format_exc()}"
                logger.error(error_msg)
                emailclient.send_email(
                    subject="Media Parsing Error in WAHA Parser file",
                    body=f"An error occurred while parsing media from WhatsApp:\n\n{error_msg}"
                )

        
        if msg_body:
            try:
                return IncomingMessage(
                    sender_id=sender_id,
                    msg_type="text",
                    text=msg_body
                )
            except Exception as text_err:
                logger.error(f"Error creating IncomingMessage for WAHA text: {text_err}")
                emailclient.send_email(
                    subject="Text Message Parsing Error in WAHA Parser file",
                    body=f"An error occurred while parsing a WhatsApp text message:\n\n{str(text_err)}"
                )

        return None

    except Exception as e:
       
        full_error = f"Fatal Error in parse_waha_message:\n{traceback.format_exc()}\nPayload Data: {payload}"
        logger.critical(full_error)
        
       
        emailclient.send_email(
            subject="Fatal Error in WAHA Message Parser file",
            body=full_error
        )
        return None