import logging
import traceback
from service.message_processor import IncomingMessage
from notified_center.EmailSender import EmailClient

logger = logging.getLogger(__name__)
emailclient = EmailClient()

def parse_facebook_message(event):
    """
    تحليل رسائل Facebook Messenger مع معالجة الأخطاء والتنبيه عبر الإيميل
    """
    try:
        # 1. التحقق الأساسي من الـ Payload
        if not isinstance(event, dict):
            return None

        msg = event.get("message")
        
        # تجاهل الرسائل المرتدة (echo) أو الرسائل الفارغة
        if not msg or msg.get("is_echo"):
            return None

        # 2. استخراج ID المرسل مع حماية ضد KeyError
        try:
            sender_id = event["sender"]["id"]
        except KeyError:
            logger.warning("Facebook event received without sender ID")
            emailclient.send_email(
                subject="Missing Sender ID in Facebook Message facebook parser file",
                body=f"A Facebook message event was received without a sender ID:\n\n{event}")
            return None

        # 3. معالجة المرفقات (Attachments)
        if "attachments" in msg:
            try:
                attachments = msg.get("attachments", [])
                if not attachments:
                    return None
                    
                att = attachments[0]
                att_type = att.get("type")   # image, file, video, audio
                payload = att.get("payload", {})
                
                # تحويل "file" إلى "document" للتوافق مع نظام OCR
                if att_type == "file":
                    mime_type = payload.get("mime_type", "").lower()
                    url = payload.get("url", "").lower()
                    
                    if "pdf" in mime_type or ".pdf" in url:
                        att_type = "document"
                
                return IncomingMessage(
                    sender_id=sender_id,
                    msg_type=att_type,
                    media=payload
                )
            except Exception as att_err:
                error_msg = f"Error parsing FB attachment: {str(att_err)}\n{traceback.format_exc()}"
                logger.error(error_msg)
                emailclient.send_email(
                    subject="Attachment Parsing Error in Facebook Parser file",
                    body=f"An error occurred while parsing an attachment from Facebook:\n\n{error_msg}")

        # 4. معالجة النصوص
        if "text" in msg:
            try:
                return IncomingMessage(
                    sender_id=sender_id,
                    msg_type="text",
                    text=msg["text"]
                )
            except Exception as text_err:
                logger.error(f"Error creating IncomingMessage for text: {text_err}")
                emailclient.send_email(
                    subject="Text Message Parsing Error in Facebook Parser file",
                    body=f"An error occurred while parsing a text message from Facebook:\n\n{str(text_err)}")

        return None

    except Exception as e:
        # خطأ غير متوقع بالكامل (Fatal Error)
        full_error = f"Fatal Error in parse_facebook_message:\n{traceback.format_exc()}\nEvent Data: {event}"
        logger.critical(full_error)
        
        # إرسال إيميل فوري للمبرمجين
        emailclient.send_email(
            subject="Fatal Error in Facebook Message Parser file",
            body=full_error)
        return None