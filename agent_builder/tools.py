from typing import Union, Optional
from langchain_core.tools import tool
from .services import BookingService, check_numofexmantionsService


@tool
def book_appointment(
    patient_name: str,
    service_name: str,
    appointment_date: str,
    phone_number: str,
) -> dict:
    """
    Book a medical appointment for a patient.
    Only call this when you have: Name, Service, Date, and Phone, AND the user confirms.
    Args:
        patient_name: Full name of the patient.
        service_name: The medical service to book.
        appointment_date: The date of the appointment.
        phone_number: the phone of the petient
    """
    result = BookingService.book(
        patient_name=patient_name,
        service_name=service_name,
        date=appointment_date,
        phone_number=phone_number
    )
    if result:
        return {
            "status": "success",
            "label": "booking_success",
            "patient_name": patient_name,
            "service_name": service_name,
            "appointment_date": appointment_date,
            "phone_number": phone_number,
            "message": f"✅ تم تأكيد حجزك يا {patient_name}!\n📍 الموعد: {appointment_date}\n🏥 الخدمة: {service_name}\n\nننتظرك في العيادة."
        }
    else:
        return {
            "status": "error", 
            "label": "booking_failed",
            "message": "❌ عذراً، واجهت مشكلة في تسجيل الحجز. سيتواصل معك الموظف المختص."
        }


@tool
def check_numofexmantions(patient_id: str) -> dict:
    """
    Check and consume free consultation session or labs and scans results using the Patient ID.
    Returns a dictionary with status, message for the patient, and a label for logging.

    """
    class DummyClinic:
        clinic_id = 1
        page_id = "dummy_page"
        api_key = "key123"
        clinic_id = 1
        page_id = "dummy_id"
        page_token = "dummy_token" # السطر اللي كان ناقص
        api_key = "key123"
        api_url = "http://waha_1:3000"
    from platforms.waha import WAHAHandler
    waha=WAHAHandler(DummyClinic)

    # 1. التحقق من وجود المريض ورصيده
    result = check_numofexmantionsService.check_numofexmantions(id_for_examination=patient_id)

    if result == "not_found":
        return {
            "status": "failed",
            "label": "patient_not_found",
            "patient_id": patient_id,
            "message": "عذراً، رقم المريض غير مسجل لدينا. يرجى التأكد من الرقم."
        }
    
    if result == "error":
        return {
            "status": "error",
            "label": "technical_error",
            "message": "حدث خطأ فني في السيرفر، يرجى المحاولة لاحقاً."
        }

    try:
        num = int(result)
    except (ValueError, TypeError):
        return {
            "status": "error",
            "label": "parsing_error",
            "message": "حدث خطأ فني في قراءة رصيد الاستشارات."
        }

    # 2. التحقق من توافر رصيد (أكبر من 0)
    if num > 0:
        success = check_numofexmantionsService.decrement_examination(id_for_examination=patient_id)
        if success:


            # إخطار الدكتور عبر WAHA
            doctor_id = "201018654380@c.us"
            doctor_message = f"إخطار: تم استخدام استشارة من المريض رقم {patient_id}. المتبقي له: {num - 1}"
            try:
                # افترضنا أن waha متاح global أو كـ instance
                waha.send(sender_id=doctor_id, text=doctor_message)
            except Exception as e:
                print(f"[ERROR] Failed to notify doctor: {e}")

            return {
                "status": "success",
                "label": "consultation_success",
                "patient_id": patient_id,
                "remaining": num - 1,
                "message": "تم التحقق بنجاح! تم إرسال رسالتك للدكتور."
            }
        else:
            return {
                "status": "failed",
                "label": "update_failed",
                "message": "حدثت مشكلة أثناء تحديث الرصيد، يرجى التواصل مع السكرتارية."
            }
    else:
        # حالة استنفاذ الرصيد
        return {
            "status": "failed",
            "label": "balance_exhausted",
            "patient_id": patient_id,
            "message": "نعتذر، لقد استنفذت جميع الاستشارات المجانية المتاحة لهذا الكود."
        }
