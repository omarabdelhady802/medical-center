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
    Check and consume free consultation sessions or labs and scans results using the Patient ID.
    Returns a dictionary with status, message for the patient, and a label for logging.
    """
    # 1. التحقق من وجود المريض ورصيده من خلال الـ Service
    result = check_numofexmantionsService.check_numofexmantions(id_for_examination=patient_id)

    if result == "not_found":
        return {
            "status": "failed",
            "label": "patient_not_found",
            "patient_id": patient_id,
            "message": "أهلاً بك، نتشرف بزيارتك للعيادة أولاً لإجراء الفحوصات اللازمة لتحديد الحالة والحل المناسب. هل تود معرفة المواعيد المتاحة للحجز الآن؟"
        }

    if result == "error":
        return {
            "status": "error",
            "label": "technical_error",
            "message": "حدث خطأ فني في السيرفر، يرجى المحاولة لاحقاً."
        }

    # 2. محاولة تحويل النتيجة لرقم (عدد الاستشارات المتبقية)
    try:
        num = int(result)
    except (ValueError, TypeError):
        return {
            "status": "error",
            "label": "parsing_error",
            "message": "حدث خطأ فني في قراءة رصيد الاستشارات."
        }

    # 3. إذا كان لديه رصيد، يتم خصم جلسة واحدة
    if num > 0:
        success = check_numofexmantionsService.decrement_examination(id_for_examination=patient_id)
        if success:
            # ملاحظة: تم نقل عملية الـ Database Save إلى الـ Agent نفسه
            # لتجنب الـ Circular Import والـ Factory Function.
            return {
                "status": "success",
                "label": "consultation_success",
                "patient_id": patient_id,
                "remaining": num - 1,
                "message": "تم استلام استفسارك وجارٍ عرضه على الدكتور المختص، وسيتم الرد عليك خلال 48 ساعة. في الحالات الطارئة يرجى التواصل مع العيادة هاتفياً، كما يمكنني حجز موعد لك الآن."
            }
        else:
            return {
                "status": "failed",
                "label": "update_failed",
                "message": "حدثت مشكلة أثناء تحديث الرصيد، يرجى التواصل مع السكرتارية."
            }
    else:
        # 4. إذا كان الرصيد 0
        return {
            "status": "failed",
            "label": "balance_exhausted",
            "patient_id": patient_id,
            "message": "عذراً، هذه الخدمة غير متاحة حالياً . يرجى التكرم بحجز موعد للزيارة في العيادة للكشف والمتابعة."
        }