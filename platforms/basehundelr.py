import json
import re
import traceback
from agent_builder.medical_agent import MedicalAgent
from extraction.chatOcr import OCRAssistant
from service.voice_transcription import VoiceService
voice_service = VoiceService()
from notified_center.EmailSender import EmailClient
from agent_builder.services import MemoryService
emailclient = EmailClient()
memory_service = MemoryService()

class BaseChatHandler:
    platform_id = None

    def __init__(self, clinic_page):
        self.clinic_page = clinic_page
        self.page_id = clinic_page.page_id
        self.api_key = clinic_page.page_token
        
        # تهيئة OCR Assistant
        self.ocr = OCRAssistant()

    def handle(self, message):
        """المُوجه الرئيسي للرسائل"""
        if message.type == "text":
            return self.handle_text(message.sender_id, message.text)
        
        if message.type == "image":
            return self.handle_image_ocr(message)
        
        if message.type == "document":
            return self.handle_pdf_ocr(message)
        if message.type == "voice" or message.type == "audio":
            return self.handle_voice(message)
                                              
        
        return self.handle_media(message.type, message.media)

    def handle_text(self, sender_id, text):
        """معالجة النصوص بواسطة MedicalAgent"""
        agent = MedicalAgent(
            platform_id=self.platform_id,
            clinic_id=self.clinic_page.clinic_id,
            page_id=self.page_id,
            sender_id=sender_id,
            
        )
        return agent.chat(text)
        

    def handle_image_ocr(self, message):
        """معالجة الصور بـ OCR"""
        try:
            image_data = self.download_image(message.media)
            if not image_data:
                return self.send(message.sender_id, "❌ فشل تحميل الصورة. حاول مرة أخرى.")
            
            ocr_input = {
                "image_binary": image_data,
                "image_ext": self._get_image_ext(message.media)
            }
            
            result = self.ocr.reply(message.sender_id, ocr_input)
            return self._process_ocr_result(result, message.sender_id)
            
        except Exception as e:
            print(f"[ERROR] Image OCR failed: {e}")
            emailclient.send_email(
                subject="Image OCR Error in chatOcr file in baseChatHandler",
                body=f"An error occurred in handle_image_ocr method: {e}")
            traceback.print_exc()
            return self.send(message.sender_id, "❌ حدث خطأ أثناء تحليل الصورة.")

    def handle_pdf_ocr(self, message):
        """معالجة ملفات PDF بـ OCR"""
        try:
            pdf_data = self.download_pdf(message.media)
            if not pdf_data:
                return self.send(message.sender_id, "❌ فشل تحميل الملف. حاول مرة أخرى.")
            
            ocr_input = {"pdf_binary": pdf_data}
            result = self.ocr.reply(message.sender_id, ocr_input)
            return self._process_ocr_result(result, message.sender_id)
            
        except Exception as e:
            print(f"[ERROR] PDF OCR failed: {e}")
            emailclient.send_email(
                subject="PDF OCR Error in chatOcr file in baseChatHandler",
                body=f"An error occurred in handle_pdf_ocr method: {e}")
            traceback.print_exc()
            return self.send(message.sender_id, "❌ حدث خطأ أثناء تحليل الملف.")

    # ================== المساعدات الذكية (Logic) ==================

    def _process_ocr_result(self, result, sender_id):
        try:
            output = result.get("output", "")
            if not output:
                self.send(sender_id, "❌ الملف فارغ أو غير واضح.")
                return

            output_str = str(output).upper()

            if "SPAM" in output_str:
                self.send(sender_id, "⚠️ عذراً، هذا المستند لا يبدو ملفاً طبياً.")
                return

            # --- 2. حالة التحاليل أو الأشعة (الـ Logic المطلوب) ---
            if "LAB_RESULT" in output_str or "SCAN" in output_str or "PRESCRIPTION" in output_str:
                try:
                    medical_data=json.dumps(output,ensure_ascii=False)
                except:
                    medical_data=str(output)
                
                if "LAB_RESULT" in output_str:
                    tag="[LAB_ANALYSIS]"
                elif "SCAN" in output_str:
                    tag="[SCAN_ANALYSIS]"    
                else:
                    tag="[PRESCRIPTION_ANALYSIS]"
                agent_reply=self.handle_text(sender_id,f"{tag}\n{medical_data}")
                self.send(sender_id,agent_reply)
                return
           

            self.send(sender_id, "📄 استلمت مستندك، كيف يمكنني مساعدتك؟")

        except Exception as e:
            # الحفاظ على الـ Error Logging
            print(f"[ERROR] Process OCR failed: {e}")
            emailclient.send_email(
                subject="OCR Process Error",
                body=f"Error processing result for {sender_id}: {e}"
            )
            traceback.print_exc()
            return self.send(sender_id, "❌ حدث خطأ أثناء معالجة الملف.")
        
    
    def handle_voice(self,message):
        audio_bytes = self.download_voice(message.media)
        if not audio_bytes:
            return self.send(message.sender_id, " فشل تحميل الرسالة الصوتية. حاول مرة أخرى.")
        text = voice_service.transcribe(audio_bytes)
        return self.handle_text(message.sender_id, text)

    def _get_image_ext(self, media):
        if not media: return ".jpg"
        mime = media.get("mimetype", "").lower()
        extensions = {"image/png": ".png", "image/webp": ".webp", "image/bmp": ".bmp"}
        return extensions.get(mime, ".jpg")

    # ========== دوال يجب تنفيذها في الـ Subclasses (FB / WA) ==========
    
    def download_image(self, media): raise NotImplementedError()
    def download_pdf(self, media): raise NotImplementedError()
    def send(self, sender_id, text): raise NotImplementedError()
    def download_voice(self, media): raise NotImplementedError()