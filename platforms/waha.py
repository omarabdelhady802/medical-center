import requests
import os
import base64
from platforms.basehundelr import BaseChatHandler

class WAHAHandler(BaseChatHandler):
    platform_id = 2

    def __init__(self, clinic_page):
        super().__init__(clinic_page)
        
        # 🔹 Hard-coded Distribution
        if clinic_page.clinic_id == 1:
            self.api_url = "http://waha_1:3000"
        elif clinic_page.clinic_id == 2:
            self.api_url = "http://waha_2:3000"
        else:
            self.api_url = "http://waha_1:3000"
          
        self.clean_key = str(self.api_key).strip() if self.api_key else ""
        
        self.headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.clean_key
        }

    def send(self, sender_id, text):
        """إرسال رسالة مع حماية ضد النصوص الفارغة وتنسيق المسافات"""
        if not text or str(text).strip() == "":
            print("[WARNING] Attempted to send empty text, skipping...")
            return None

        url = f"{self.api_url}/api/sendText"
        payload = {
            "session": "default",
            "chatId": sender_id,
            "text": str(text)
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code not in [200, 201]:
                print(f"[ERROR] WAHA returned {response.status_code}: {response.text}")
            else:
                print(f"[DEBUG] Message sent successfully to {sender_id}")
            
            # ✅ التعديل هنا: لا ترجع كائن الـ response أبداً للمستخدم
            return None 
            
        except Exception as e:
            print(f"[ERROR] Failed to connect to WAHA: {e}")
            return None

    def download_image(self, media):
        """تحميل الصور/الملفات من WAHA"""
        try:
            if "data" in media:
                return base64.b64decode(media["data"])
            
            url = media.get("url")
            if url:
                if "localhost" in url:
                    # استخراج الـ Hostname من api_url (مثلاً waha_1)
                    host = self.api_url.split("//")[1].split(":")[0]
                    url = url.replace("localhost", host)
                
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                return response.content
            
            return None
        except Exception as e:
            print(f"[ERROR] WAHA Download Error: {e}")
            return None

    def download_pdf(self, media):
        return self.download_image(media)