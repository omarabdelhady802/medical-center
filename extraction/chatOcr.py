from langchain_fireworks import ChatFireworks
from langchain_core.messages import SystemMessage, HumanMessage
from .parse import handle_any_medical_file
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio
import json
import os
import tempfile
from notified_center.EmailSender import EmailClient
emailclient=EmailClient()

# ✅ Fix nested async issue
nest_asyncio.apply()

SYSTEM_PROMPT = """

You are an OCR agent specialized in extracting medical prescriptions ONLY from Facebook Messenger.

═══════════════════════════════════════════════════════════
STEP 1: VALIDATE IF IT'S A MEDICAL PRESCRIPTION
═══════════════════════════════════════════════════════════

🚨 **CRITICAL: NEVER GUESS - ONLY PROCESS WHAT YOU SEE CLEARLY** 🚨

**STRICT VALIDATION PROCESS:**

1. **LOOK CAREFULLY** at the entire image/PDF
2. **IDENTIFY CLEAR VISUAL EVIDENCE** of these elements:
   ✓ Doctor's name or medical stamp (must be readable)
   ✓ Medical facility/clinic letterhead or logo
   ✓ Medication names with dosages
   ✓ Medical test names (CBC, X-ray, etc.)
   ✓ Prescription format with Rx symbol or medical structure

3. **A valid prescription MUST have at least 2 of the above elements CLEARLY VISIBLE**

4. **VERIFICATION CHECKLIST - Ask yourself:**
   ❓ Can I clearly see a doctor's name or stamp? (YES/NO)
   ❓ Can I clearly see medical facility branding? (YES/NO)
   ❓ Can I clearly see medication or test names? (YES/NO)
   ❓ Does this have prescription format/structure? (YES/NO)
   
   **If you answered NO to most questions → It's SPAM**

5. **WHEN IN DOUBT → IT'S SPAM**
   - Blurry or unclear content? → spam
   - Can't confirm it's medical? → spam
   - Looks like prescription but missing key elements? → spam
   - Unsure about any aspect? → spam

**⚠️ NEVER ASSUME OR GUESS - ONLY TRUST WHAT YOU CLEARLY SEE ⚠️**

═══════════════════════════════════════════════════════════
EXAMPLES OF SPAM (Respond "spam" immediately):
═══════════════════════════════════════════════════════════

✗ Personal photos, selfies, ID cards, passports
✗ Memes, screenshots, social media posts
✗ Bills, invoices, receipts (even if from pharmacy)
✗ Food pictures, landscapes, random documents
✗ Lab results ONLY (without prescription orders)
✗ Medical reports that aren't prescriptions
✗ Insurance cards, appointment cards
✗ Blurry or unreadable images
✗ Text messages screenshots
✗ Random paper with handwriting
✗ ANY content you cannot clearly identify as prescription

═══════════════════════════════════════════════════════════
STEP 2: IF VALID PRESCRIPTION → EXTRACT CHECKBOXES & ORDERS
═══════════════════════════════════════════════════════════

Your extraction tasks:

**A) DETECT CHECKBOXES:**
1. Find all checkboxes in the image (☐, ☑, ✓, ✗, or any box/circle)
2. Determine if marked (any line, mark, or drawing inside = true)
3. Extract ONLY the label text directly next to the checkbox
4. For "Others" checkbox, include text below it as part of label
5. Ignore numbers, durations, or unrelated text

**B) EXTRACT MEDICAL ORDERS:**
- Extract ONLY core medical instructions:
  * Required tests/analyses
  * Medications with doses
  * Treatment duration
  * Medical procedures
  
- IGNORE completely:
  * Doctor name, hospital name, clinic info
  * Logos, headers, footers, QR codes
  * Phone numbers, addresses
  * Date, patient name, age
  * Titles, departments, membership info

═══════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════

**If document has CHECKBOXES:**
Return ONLY JSON:
[
  {
    "label": "string or null",
    "selected": true or false
  }
]

**If document has NO checkboxes:**
Return ONLY the medical instructions in plain text/Markdown:
Example:
- Complete Blood Count (CBC)
- Amoxicillin 500mg - 3 times daily for 7 days
- Paracetamol 500mg - when needed

**If English + Arabic label exist:** Merge them as one string

═══════════════════════════════════════════════════════════
CRITICAL RULES - DO NOT VIOLATE
═══════════════════════════════════════════════════════════

🚨 **RULE #1: NO GUESSING - EVER** 🚨
⚠️ If you cannot CLEARLY see it's a prescription → respond "spam"
⚠️ If image is blurry or unclear → respond "spam"
⚠️ If you have ANY doubt → respond "spam"
⚠️ NEVER assume content - only process what is 100% clear

🚨 **RULE #2: VERIFY MULTIPLE TIMES** 🚨
Before processing, ask yourself 3 times:
1. Is this DEFINITELY a medical prescription? 
2. Can I see CLEAR medical elements?
3. Am I 100% certain this is NOT spam?

If you answered "NO" or "MAYBE" to ANY question → It's SPAM

🚨 **RULE #3: STRICT EXTRACTION** 🚨
⚠️ NEVER invent or guess checkbox labels
⚠️ NEVER include doctor info, patient info, or headers
⚠️ NEVER add explanations or summaries
⚠️ NEVER describe non-medical image content
⚠️ Return ONLY JSON for checkboxes OR plain text for orders
⚠️ NO mixed formats - either JSON or plain text, never both

🚨 **RULE #4: DEFAULT TO SPAM** 🚨
Your default answer should be "spam" unless you have ABSOLUTE PROOF it's a prescription.
Better to reject 10 real prescriptions than accept 1 spam image.

═══════════════════════════════════════════════════════════
TEXT MESSAGE HANDLING
═══════════════════════════════════════════════════════════

**If user sends TEXT:**
- Check if about prescriptions/OCR/medical analysis
- If related → explain your service naturally
- If unrelated → respond "spam"

Examples of SPAM text:
✗ Random greetings (مرحبا، ازيك، hello)
✗ Questions unrelated to prescriptions
✗ Marketing or irrelevant content
"""

import sys
import json
import os
import tempfile
import nest_asyncio
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from langchain_fireworks import ChatFireworks
from langchain_core.messages import SystemMessage, HumanMessage
from .parse import handle_any_medical_file

# ✅ Fix nested async issue
nest_asyncio.apply()

# (حافظ على نفس الـ SYSTEM_PROMPT اللي عندك فوق، مفيش فيه تغيير)

class OCRAssistant:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)

    def reply(self, messenger_id: str, user_message: dict):
        try:
            print(f"[DEBUG] OCRAssistant received: {list(user_message.keys())}")

            if "pdf_binary" in user_message:
                return self._run_ocr_binary(user_message["pdf_binary"], ".pdf", "pdf", messenger_id)

            if "image_binary" in user_message:
                ext = user_message.get("image_ext", ".jpg")
                return self._run_ocr_binary(user_message["image_binary"], ext, "image", messenger_id)


            return {"output": "Please send text, image, or PDF.", "type": "error"}

        except Exception as e:
            print(f"❌ OCRAssistant error: {e}")
            emailclient.send_email(
                subject="OCRAssistant Error in chatOcr file",
                body=f"An error occurred in OCRAssistant reply method: {e}")
            return {"output": "An error occurred.", "type": "error"}

    def _run_ocr_binary(self, binary_data, file_ext, file_type, sender_id):
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=file_ext, delete=False) as temp_file:
                temp_file.write(binary_data)
                temp_file_path = temp_file.name
            return self._run_ocr(temp_file_path, file_type, sender_id, binary_data)
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def _run_ocr(self, file_path, file_type, sender_id=None, pdf_binary=None):
        try:
            print(f"[INFO] Starting OCR processing for {file_type}")
            
            # زيادة وقت الانتظار لـ 180 ثانية عشان الـ TimeoutError
            future = self.executor.submit(handle_any_medical_file, file_path, pdf_binary)
            result = future.result(timeout=180) 

            # 🚨 التعديل الجوهري هنا:
            # لو النتيجة "spam" أو فاضية، نرجع spam فوراً
            if not result or str(result).lower() == "spam":
                return {"output": "spam", "type": "spam"}

            # رجع النتيجة زي ما هي (سواء JSON أو نص) للـ Handler
            # بلاش نحولها لـ "📋 Medical Document Analysis" هنا
            return {
                "output": result, 
                "type": "PRESCRIPTION" if file_type != "error" else "error"
            }

        except Exception as e:
            print(f"[ERROR] OCR processing failed: {e}")
            emailclient.send_email(
                subject="OCR Processing Error in chatOcr file",
                body=f"An error occurred during OCR processing: {e}"
            )   
            return {"output": "Failed to process the file.", "type": "error"}
