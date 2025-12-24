from app import app
from models.models import db, ClinicBranch, ClinicPage, Platform

def setup_medical_system():
    with app.app_context():
        db.drop_all()
        # 1. إنشاء الجداول لو مش موجودة
        db.create_all()

        # 2. إضافة منصة فيسبوك (ID = 1)
        if not Platform.query.get(1):
            db.session.add(Platform(id=1, name="Facebook Messenger"))
            print("✅ Platform Facebook added.")

        # 3. إضافة بيانات العيادة والـ Sub-services
        # تأكد إنك تغير الـ page_id للرقم الحقيقي بتاع صفحتك
        YOUR_REAL_PAGE_ID = "828692133669410" # <--- حط الـ ID بتاع صفحتك هنا
        
        # بنشيك لو العيادة موجودة قبل كدة عشان م نكررهاش
        clinic = ClinicBranch.query.filter_by(name="Heart Center").first()
        if not clinic:
            clinic = ClinicBranch(
                name="Heart Center",
                address="القاهرة - مدينة نصر - شارع الطيران",
                services="كشف قلب: 400 جنيه، رسم قلب: 200 جنيه، إيكو: 600 جنيه",
                subservices="رقم التليفون للطوارئ: 01208140337، مواعيد المعمل: يومياً من 9 ص لـ 10 م"
            )
            db.session.add(clinic)
            db.session.flush() # عشان نطلع الـ ID بتاع العيادة فوراً
            print("✅ Clinic and Sub-services added.")

        # 4. ربط العيادة بالـ Page ID
        page_link = ClinicPage.query.filter_by(page_id=YOUR_REAL_PAGE_ID).first()
        if not page_link:
            page_link = ClinicPage(
                page_id=YOUR_REAL_PAGE_ID,
                clinic_id=clinic.id,
                platform_id=1,
                page_token="EAFZAh4EiZCf0cBQeYCanULFLYZAiALeDfFAVfWsjyfRgGCjBcmeNYQ04Drq3ZCN1w579LQZAhTyOJO7pIbzgrYhHuB6dtcZBQwmRG1WjcHbhcYhegtACeVZBQZC7YbasOr0ZC0SwNp65ncxZCYZCyhLCpFJn4uEuf7ZCzcdeZBz77szFanYHaRZA5iDWrQyWLUFIuZBB8pQpZAyE4gZDZD" # اختيارياً
            )
            db.session.add(page_link)
            print(f"✅ Clinic linked to Page ID: {YOUR_REAL_PAGE_ID}")

        db.session.commit()
        print("🚀 System is Ready to receive messages!")

if __name__ == "__main__":
    setup_medical_system()