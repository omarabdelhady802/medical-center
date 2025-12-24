import pandas as pd
import os
from datetime import datetime
from models.models import db

class BookingService:
    @staticmethod
    def book(client, service_name, date):
        
        booking_data = {
            "Patient Name": [client.sender_id], # أو أي اسم متاح
            "Service": [service_name],
            "Date": [date],
            "Booking Time": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        }
        
        df_new = pd.DataFrame(booking_data)
        file_name = "bookings.xlsx"

        # 3. حفظ في ملف Excel (لو موجود يزود عليه، لو مش موجود يكريته)
        if not os.path.isfile(file_name):
            df_new.to_excel(file_name, index=False)
        else:
            with pd.ExcelWriter(file_name, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                # بنجيب آخر سطر في الشيت عشان نزود بعده
                try:
                    existing_df = pd.read_excel(file_name)
                    df_new.to_excel(writer, index=False, header=False, startrow=len(existing_df) + 1)
                except:
                    df_new.to_excel(writer, index=False)

        print(f"✅ Booking saved to Excel: {service_name} for {client.sender_id}")

class MemoryService:
    @staticmethod
    def update(client, summary, last_reply):
        client.chat_summary = (summary or "")[:500]
        client.last_bot_reply = last_reply
        db.session.commit()
