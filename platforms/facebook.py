import requests
from platforms.basehundelr import BaseChatHandler


class FacebookHandler(BaseChatHandler):
    platform_id = 1

    def send(self, sender_id, text):
        """
        إرسال رسالة على Facebook Messenger
        """
        response = requests.post(
            "https://graph.facebook.com/v17.0/me/messages",
            json={
                "recipient": {"id": sender_id},
                "message": {"text": text}
            },
            params={"access_token": self.api_key},
            timeout=10
        )
        return response.ok
    
    def download_image(self, media):
        """
        تحميل صورة من Facebook
        
        Facebook بيبعت URL في الـ payload
        نستخدمه لتحميل الصورة
        """
        try:
            url = media.get("url")
            if not url:
                print("[ERROR] No URL in media payload")
                return None
            
            print(f"[INFO] Downloading image from Facebook: {url[:60]}...")
            
            # تحميل الصورة
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            print(f"[INFO] Image downloaded successfully: {len(response.content)} bytes")
            return response.content
            
        except requests.exceptions.Timeout:
            print("[ERROR] Timeout while downloading image")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to download image from Facebook: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading image: {e}")
            return None
    
    def download_pdf(self, media):
        """
        تحميل PDF من Facebook
        
        نفس طريقة download_image
        Facebook بيتعامل مع الـ PDF كـ file attachment
        """
        try:
            url = media.get("url")
            if not url:
                print("[ERROR] No URL in media payload")
                return None
            
            print(f"[INFO] Downloading PDF from Facebook: {url[:60]}...")
            
            # تحميل الـ PDF (timeout أطول لأن PDF أكبر حجماً)
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            
            print(f"[INFO] PDF downloaded successfully: {len(response.content)} bytes")
            return response.content
            
        except requests.exceptions.Timeout:
            print("[ERROR] Timeout while downloading PDF")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to download PDF from Facebook: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading PDF: {e}")
            return None