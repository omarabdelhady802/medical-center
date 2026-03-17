import os
import io
import logging
import time
import httpx

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.mistral_api_key = "lL60Z9ACii046sbxzS8BzBxlcCy9cbKg"

    def transcribe(self, audio_bytes):
        if not audio_bytes:
            return ""

        start = time.time()
        result = self._transcribe_voxtral(audio_bytes)
        elapsed = time.time() - start

        logger.info(f"⏱️ Total transcription time: {elapsed:.2f}s")
        print(f"Final transcription: {result}")
        return result

    def _transcribe_voxtral(self, audio_bytes):
        try:
            with httpx.Client(timeout=30) as client:
              response = client.post(
                "https://api.mistral.ai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.mistral_api_key}"},
                files={
                    "file": ("audio.ogg", audio_bytes, "audio/ogg")
                },
                data={
                    "model": "voxtral-mini-2602",  
                    "language": "ar",
                }
            )
            
            # اطبع الـ response الكامل عشان نشوف المشكلة
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            response.raise_for_status()
            text = response.json().get("text", "")
            return text

        except Exception as e:
           logger.error(f"Voxtral transcription failed: {e}")
           return ""