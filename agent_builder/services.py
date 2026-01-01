import pandas as pd
import os
from datetime import datetime,timedelta, timezone
from models.models import db


class BookingService:
    
    @staticmethod
    def book(patient_name, service_name, date, phone_number):
        file_name = "bookings.xlsx"
        
        booking_data = {
            "Patient Name": patient_name,
            "Service": service_name,
            "Date": date,
            "Phone Number": phone_number,
            "Booking Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            if os.path.isfile(file_name):
                df_existing = pd.read_excel(file_name)
                df_new = pd.concat([df_existing, pd.DataFrame([booking_data])], ignore_index=True)
            else:
                df_new = pd.DataFrame([booking_data])

            df_new.to_excel(file_name, index=False)
            print(f"✅ Booking saved to Excel")
            
            return True  # 👈 السطر ده أهم حاجة! لازم نرجع True عشان الـ Tool تحس بالنجاح
            
        except Exception as e:
            print(f"❌ Excel Error: {e}")
            return False # 👈 ونرجع False لو حصلت مشكلة
        
        
class MemoryService:
    @staticmethod
    def update(client, summary, last_reply):
        try:
            client.chat_summary = (summary or "")
            client.last_bot_reply = last_reply
            client.expiration_date = datetime.now(timezone.utc) + timedelta(days=2)

            db.session.add(client)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"❌ Database Memory Error: {e}")