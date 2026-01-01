from llama_parse import LlamaParse
import fitz  
import os
import json
import re
import cv2
import numpy as np
import io
from notified_center.EmailSender import EmailClient
email_client = EmailClient()


# ------------------------ PROMPT ------------------------
improved_prompt = """
You are a medical document classifier and extractor.

## STEP 1: Document Type Classification
Analyze the input and categorize into EXACTLY ONE type:

1. **PRESCRIPTION**: Doctor's order for medication/treatment
   - Contains: Drug names, dosages, frequencies, durations
   - May have: Checkboxes for tests/examinations
   - Format: Handwritten or printed prescription

2. **SCAN**: Medical imaging reports
   - Contains: X-ray, MRI, CT, Ultrasound, ECHO
   - Usually: Visual images on dark backgrounds or radiology reports

3. **LAB_RESULT**: Laboratory test results
   - Contains: Tables with test names, results, units, reference ranges
   - Examples: Blood tests, urine tests, biochemistry panels

4. **SPAM**: Anything else (non-medical or unrelated)

---

## STEP 2: Content Extraction Rules

### For PRESCRIPTION:
Extract in this priority order:

**A. If checkboxes exist:**
- Extract ALL checkboxes with their labels and selection status
- Each checkbox becomes one JSON object

**B. If NO checkboxes:**
- Extract the core medical instructions ONLY
- Each instruction/medication becomes one JSON object
- Include: Medication names, dosages, frequencies, durations
- Exclude: Doctor name, clinic info, patient name, date, logos

**C. Special handling for "Others" checkbox:**
- If "Others" is checked, include the handwritten text next to/below it in the label

### For SCAN:
Return single JSON object with document_type "SCAN"

### For LAB_RESULT:
Return single JSON object with document_type "LAB_RESULT"

### For SPAM:
Return single JSON object with document_type "SPAM"

---

## CHECKBOX EXTRACTION RULES (for PRESCRIPTION only):

1. **Detection**: Look for visual indicators: ☐ ☑ ✓ ✗ □ ■ X or any box/circle
2. **Selection Status**:
   - `selected: true` if checkbox contains ANY mark (✓, ✗, X, line, dot, scribble)
   - `selected: false` if checkbox is empty
3. **Label Extraction**:
   - Extract the text directly next to the checkbox
   - If English + Arabic exist, return English only
   - If no readable label, use `"label": null`
4.**Look at checkbox me and bring the title that belongs to her. Look at the whole row**.
5.The titles you choose[Examination (s) Required,Holter,ABPM,patch heart monitor]
---

## CRITICAL OUTPUT RULES:

🚨 **ALWAYS return JSON array format with this EXACT structure:**

```json
[
  {
    "document_type": "string",
    "title": "string or null",
    "label": "string or null",
    "selected": true or false
  }
]
```

🚨 **NEVER return:**
- HTML tables
- Markdown tables
- Plain text paragraphs
- Explanations or summaries

🚨 **For tables with checkboxes:**
- Convert each row to a separate JSON object
- Merge checkbox status with its label
- Return as JSON array

🚨 **Ignore completely:**
- Doctor/hospital names, logos, headers, footers
- Phone numbers, addresses, QR codes
- Patient name, date, membership info
- Department names, clinic information

---

## OUTPUT EXAMPLES:





### Example 4: X-ray or any medical scan image
**Output:**
```json
[
  {
    "document_type": "SCAN",
    "title": null,
    "label": null,
    "selected": false
  }
]
```

### Example 5: Lab result report
**Output:**
```json
[
  {
    "document_type": "LAB_RESULT",
    "title": null,
    "label": null,
    "selected": false
  }
]
```

### Example 6: Non-medical content (recipe, note, etc.)
**Output:**
```json
[
  {
    "document_type": "SPAM",
    "title": null,
    "label": null,
    "selected": false
  }
]
```

---

## UNIFIED JSON STRUCTURE - MANDATORY FOR ALL CASES:

Every output MUST be a JSON array containing objects with these 4 fields:

```json
{
  "document_type": "PRESCRIPTION" | "SCAN" | "LAB_RESULT" | "SPAM",
  "title": "string or null",
  "label": "string or null",
  "selected": true | false
}
```


## FINAL REMINDERS:
- Analyze the ENTIRE document first before classifying
- For PRESCRIPTION: Extract medical content OR checkboxes (never doctor/clinic info)
- For SCAN/LAB_RESULT/SPAM: Return single JSON object with nulls
- NO explanations, NO summaries, NO extra text
- ONLY return valid JSON array with the EXACT 4-field structure
- ALL 4 fields are MANDATORY in every JSON object
"""




parser = LlamaParse(
    api_key="llx-g13trFlVAeD6sCl3LavrcQLAIY0eEmlj6qVsvruTLhQHzmN7",
    parse_mode="parse_page_with_lvm",
    model="openai-gpt4o",
    high_res_ocr=True,
    adaptive_long_table=True,
    outlined_table_extraction=True,
    output_tables_as_HTML=False,
    user_prompt=improved_prompt,
    verbose=True,
    
    
)
# ------------------------ PDF → IMAGES ------------------------
def pdf_to_images(pdf_binary: bytes, dpi: int = 300) -> list[bytes]:
    images = []

    doc = fitz.open(stream=pdf_binary, filetype="pdf")

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("jpeg"))

    doc.close()
    return images

# ------------------------ PREPROCESSING ------------------------


def preprocess_for_checkboxes(img_bytes: bytes) -> bytes:
    np_img = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("❌ Failed to decode image bytes")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.convertScaleAbs(gray, alpha=2.0, beta=-150)


    bw = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5
    )

    kernel = np.ones((2, 2), np.uint8)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)

    ok, out = cv2.imencode(".jpg", bw)
    if not ok:
        raise ValueError("❌ Failed to encode image")

    return out.tobytes()


# ------------------------ JSON EXTRACTION (IMPROVED) ------------------------
def extract_json(text):
    """
    Extract all JSON arrays from text that contain checkbox data.
    Handles multiple JSON structures in the same response.
    """
    all_items = []
    
   
    array_pattern = r'\[[\s\S]*?\]'
    matches = re.finditer(array_pattern, text)
    
    for match in matches:
        try:
            data = json.loads(match.group())
            
            
            if isinstance(data, list) and len(data) > 0:
                
                if isinstance(data[0], dict) and "label" in data[0] and "selected" in data[0]:
                    all_items.extend(data)
                    print(f"  ✓ Found valid checkbox array with {len(data)} items")
        except json.JSONDecodeError:
            email_client.send_email(
                subject="JSONDecodeError in parse file",
                body=f"Failed to decode JSON array from text segment: {match.group()}"
            )
            
            continue
    
    
    if not all_items:
        print(f"spam")
    
    return all_items

# ------------------------ MAIN HANDLER ------------------------


def parse_bytes_with_legacy_parser(parser, img_bytes: bytes,file_name: str = "temp.pdf"):
    img_io = io.BytesIO(img_bytes)
    extra_info = {"file_name": file_name}
    
    return parser.parse(img_io, extra_info=extra_info)




SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

def handle_any_medical_file(file_path: str, pdf_binary: bytes = None):
    file_path = os.path.abspath(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    all_outputs = []

    # ================= PDF =================
    if ext == ".pdf":
        if pdf_binary is None:
            raise ValueError("❌ pdf_binary is required for PDF processing")

        images_bytes = pdf_to_images(pdf_binary)
        print(f"📄 PDF pages detected: {len(images_bytes)}")

        for idx, img_bytes in enumerate(images_bytes, start=1):
            try:
                print(f"\n--- [{idx}] PROCESSING PDF PAGE ---")

                clean_bytes = preprocess_for_checkboxes(img_bytes)

                result = parse_bytes_with_legacy_parser(parser, clean_bytes)

                if not hasattr(result, "pages"):
                    continue

                for page_idx, page in enumerate(result.pages, start=1):

                    md = getattr(page, "md", "")

                    if not md or not md.strip():
                       print(f"⚠ Page {page_idx} spam")
                       continue
                    

                    data = extract_json(page.md)
                    for item in data:
                        document_type =item.get("document_type", None)  
                        title =  item.get("title", None)                              
                        label = item.get("label", None)  
                        selected = item.get("selected", False)  
                        
                       
                        all_outputs.append({"document_type":document_type ,"title":title,"label": label, "selected": selected})

            except Exception as e:
                print(f"❌ Error page {idx}: {e}")
                import traceback
                traceback.print_exc()

    # ================= IMAGE =================
    elif ext in SUPPORTED_IMAGE_EXTS:
        result = parser.parse(file_path)

        if hasattr(result, "pages"):
            for page in result.pages:
                md = getattr(page, "md", "")

                if not md or not md.strip():
                    continue

                data = extract_json(page.md)
                print(data)
                for item in data:
                    document_type =item.get("document_type", None)  
                    title=item.get("title", None)                                 
                    label = item.get("label", None) 
                    selected = item.get("selected", False) 
                    
                    
                    all_outputs.append({ "document_type":document_type ,"title":title,"label": label, "selected": selected})

    else:
        raise ValueError(f"❌ Unsupported file type: {ext}")

    print(f"\n{'='*60}")
    print(f"✅ Total extracted items: {len(all_outputs)}")
    print(f"{'='*60}")

    return all_outputs



if __name__ == "__main__":
    file_path = "ocr,3 pages.pdf"
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                binary_data = f.read()
            
            result = handle_any_medical_file(file_path, pdf_binary=binary_data)
            
            print("\n" + "="*60)
            print("FINAL RESULT:")
            print("="*60)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"Error processing the file: {e}")
            email_client.send_email(
                subject="File Processing Error in parse file",
                body=f"An error occurred while processing the file {file_path}: {e}"
            )
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ File not found: {file_path}")