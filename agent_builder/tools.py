from langchain_core.tools import tool
from .services import BookingService

def create_booking_tool():
    """Create a booking tool for the medical agent"""
    
    @tool
    def book_appointment(
        patient_name: str, 
        service_name: str, 
        appointment_date: str, 
        phone_number: str,
        confirmed: bool = True
    ) -> dict: # لاحظ هنا بنرجع dict مش str
        """
        Book a medical appointment for a patient. 
        Only call this tool when you have: Name, Service, Date, and Phone, AND the user confirms.
        """
        # نداء الخدمة لحفظ البيانات في الإكسيل
        result = BookingService.book(
            patient_name=patient_name, 
            service_name=service_name, 
            date=appointment_date, 
            phone_number=phone_number
        )
        
        # لازم نرجع Dictionary عشان الـ Agent يفهمه
        if result:
            return {
                "status": "success",
                "message": f"تم حجز {service_name} للمريض {patient_name}",
                "appointment_date": appointment_date
            }
        else:
            return {
                "status": "error",
                "message": "فشل الحجز في ملف الإكسيل"
            }
    
    return book_appointment