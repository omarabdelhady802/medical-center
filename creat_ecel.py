import pandas as pd
from pathlib import Path

FILE_NAME = "appointments.xlsx"
SHEET_NAME = "bookings"

# لو الملف موجود ما نعملش حاجة
if Path(FILE_NAME).exists():
    print(f"✅ {FILE_NAME} already exists.")
else:
    # إنشاء DataFrame فاضي بالأعمدة المطلوبة
    df = pd.DataFrame(columns=[
        "patient_name",
        "service_name",
        "clinic_name",
        "phone",
        "notes"
    ])

    # حفظه كـ Excel
    df.to_excel(FILE_NAME, sheet_name=SHEET_NAME, index=False)

    print(f"🆕 {FILE_NAME} created successfully with sheet '{SHEET_NAME}'.")
