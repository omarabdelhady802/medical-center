import json
import re
import traceback
from agent_builder.medical_agent import MedicalAgent
from extraction.chatOcr import OCRAssistant

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
        
        return self.handle_media(message.type, message.media)

    def handle_text(self, sender_id, text):
        """معالجة النصوص بواسطة MedicalAgent"""
        agent = MedicalAgent(
            platform_id=self.platform_id,
            clinic_id=self.clinic_page.clinic_id,
            page_id=self.page_id,
            sender_id=sender_id,
            api_key=self.api_key
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
            traceback.print_exc()
            return self.send(message.sender_id, "❌ حدث خطأ أثناء تحليل الملف.")

    # ================== المساعدات الذكية (Logic) ==================

    def _parse_ocr_output(self, output):
        """تحويل مخرج الـ OCR لبيانات حتى لو نص عادي"""
        try:
            if not output: return None
            output_str = str(output).strip()

            # 1. محاولة استخراج JSON لو موجود
            found_arrays = re.findall(r'\[[\s\S]*?\]', output_str)
            if found_arrays:
                all_data = []
                for array_str in found_arrays:
                    try:
                        data = json.loads(array_str)
                        if isinstance(data, list): all_data.extend(data)
                    except: continue
                if all_data: return all_data

            # 2. لو المخرج نص عادي
            if len(output_str) > 10:
                return [{"document_type": "PRESCRIPTION", "raw_text": output_str}]
            
            return None
        except Exception as e:
            print(f"[ERROR] Parsing failed: {e}")
            return None

    def _get_document_type(self, parsed_data):
        """تحديد النوع بمرونة عالية"""
        if not parsed_data:
            return "UNKNOWN"

        full_text_data = str(parsed_data).upper()

        if "PRESCRIPTION" in full_text_data or "روشتة" in full_text_data:
            return "PRESCRIPTION"
        
        if "SCAN" in full_text_data or "X-RAY" in full_text_data or "أشعة" in full_text_data:
            return "SCAN"
        
        if "LAB" in full_text_data or "RESULT" in full_text_data or "تحليل" in full_text_data:
            return "LAB_RESULT"

        if "SPAM" in full_text_data:
            return "SPAM"

        return "UNKNOWN"

    def _process_ocr_result(self, result, sender_id):
        output = result.get("output", "")
        if not output:
            self.send(sender_id, "❌ الملف فارغ أو غير واضح.")
            return # ارجع None وليس مخرج الـ send

        output_str = str(output).upper()

        # 1. أولوية الروشتة (حتى لو الملف فيه حاجات تانية)
        if "PRESCRIPTION" in output_str:
            print("[ACTION] Prescription detected, analyzing...")
            try:
                prescription_data = json.dumps(output, ensure_ascii=False)
            except:
                prescription_data = str(output)
            
            # نأخذ الرد من الـ Agent ونرسله
            agent_reply = self.handle_text(sender_id, f"[PRESCRIPTION_ANALYSIS]\n{prescription_data}")
            self.send(sender_id, agent_reply)
            return

        # 2. التحاليل
        if "LAB_RESULT" in output_str:
            self.send(sender_id, "📄 هذه نتائج تحاليل طبية، يرجى استشارة الطبيب. هل تحب حجز موعد لمراجعتها؟")
            return

        # 3. الأشعة
        if "SCAN" in output_str:
            self.send(sender_id, "☢️ هذا تقرير أشعة. يرجى عرضه على الطبيب المختص.")
            return

        # 4. سبام
        if "SPAM" in output_str:
            self.send(sender_id, "⚠️ عذراً، لا يمكنني معالجة هذه الصورة كروشتة طبية.")
            return

        self.send(sender_id, "📄 استلمت مستندك، كيف يمكنني مساعدتك؟")
        return

    def handle_media(self, msg_type, media):
        responses = {
            "video": "برجاء ارسال رسالة نصية بدلاً من الفيديو.",
            "audio": "برجاء ارسال رسالة نصية بدلاً من الملف الصوتي.",
            "voice": "برجاء ارسال رسالة نصية بدلاً من الرسالة الصوتية.", 
            "location": "📍 تم استلام الموقع بنجاح."
        }
        return responses.get(msg_type, "📎 تم استلام المرفق.")

    def _get_image_ext(self, media):
        if not media: return ".jpg"
        mime = media.get("mimetype", "").lower()
        extensions = {"image/png": ".png", "image/webp": ".webp", "image/bmp": ".bmp"}
        return extensions.get(mime, ".jpg")

    # ========== دوال يجب تنفيذها في الـ Subclasses (FB / WA) ==========
    
    def download_image(self, media): raise NotImplementedError()
    def download_pdf(self, media): raise NotImplementedError()
    def send(self, sender_id, text): raise NotImplementedError()