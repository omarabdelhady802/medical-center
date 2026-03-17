import pandas as pd
import os
from datetime import datetime,timedelta, timezone
from models.models import db ,Booking,Patient
from notified_center.EmailSender import EmailClient

emailclient=EmailClient()
class BookingService:
    
    @staticmethod
    def book(patient_name, service_name, date, phone_number):
        
        book =Booking.query.filter_by(
            name=patient_name, 
            services=service_name,
            date=date,
            phone_number=phone_number
        ).first() 
        if book:
            print("⚠️ Booking already exists in the database")
            return False
        else:
            new_booking = Booking(
                name=patient_name,
                services=service_name,
                date=date,
                phone_number=phone_number,
            )
            try:
                db.session.add(new_booking)
                db.session.commit()
                print("✅ Booking saved to database")
                return True
            except Exception as e:
                db.session.rollback()
                print(f"❌ Database Error: {e}")
                emailclient.send_email(
                    subject="BookingService Database Error in services file",
                    body=f"An error occurred while saving a booking: {e}"
                )
                return False
        
        
        
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
            emailclient.send_email(
                subject="MemoryService Database Error in services file",
                body=f"An error occurred while updating client memory: {e}"
            )

class check_numofexmantionsService:
    @staticmethod
    def check_numofexmantions(id_for_examination):
        try:
            patient = Patient.query.filter_by(id_for_examination=id_for_examination).first()
            
            if not patient:
                return "not_found"
            
           
            return patient.num_examination
            
        except Exception as e:
            print(f"❌ Database Error: {e}")
            return "error"
    @staticmethod
    def decrement_examination(id_for_examination):
        try:
            patient = Patient.query.filter_by(id_for_examination=id_for_examination).first()
            if patient:
                # تحويل النص لرقم قبل الطرح لأن العمود String عندك
                current_num = int(patient.num_examination or 0)
                if current_num > 0:
                    patient.num_examination = str(current_num - 1)
                    db.session.commit()
                    return True
            return False
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error decrementing: {e}")
            return False    