from langchain_core.tools import tool
from .services import BookingService

def create_booking_tool(client):
    """Create a booking tool for the medical agent"""
    
    @tool
    def book_appointment(patient_name: str, service_name: str, appointment_date: str):
        """
        Book a medical appointment for a patient.
        
        Args:
            patient_name: The full name of the patient
            service_name: The medical service to book (e.g., 'كشف قلب', 'رسم قلب')
            appointment_date: The desired appointment date
            
        Returns:
            str: Confirmation message
        """
        BookingService.book(client, service_name, appointment_date)
        return f"تم حجز موعد {service_name} للمريض {patient_name} في تاريخ {appointment_date}"
    
    return book_appointment
