from faster_whisper import WhisperModel
import io

class VoiceService:

    def __init__(self):
        self.model = WhisperModel("base")

    def transcribe(self, audio_bytes):

        audio_file = io.BytesIO(audio_bytes)

        segments, _ = self.model.transcribe(audio_file)

        text = " ".join([seg.text for seg in segments])

        return text