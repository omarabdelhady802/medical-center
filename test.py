from agent_builder.medical_agent import medical_agent
from models.models import db, ClinicBranch, ClinicPage, Client
from app import app
import os

with app.app_context():
    # 1. تنظيف الداتابيز (اختياري لو عايز تبدأ من الصفر كل مرة)
    db.drop_all()
    db.create_all()
    print("🧹 Database cleaned and recreated.")

    test_page_id = "123" 
    
    # 2. إضافة العيادة
    clinic = ClinicBranch(
        name="Heart Center",
        address="القاهرة - مدينة نصر",
        services="كشف القلب السعر 400 ،رسم قلب",
        subservices="عيادات العيون رقم التلفون 01208140337"
    )
    db.session.add(clinic)
    db.session.commit()

    page_link = ClinicPage(
        page_id=test_page_id, 
        clinic_id=clinic.id,
        platform_id=1,
        page_token="test_token"
    )
    db.session.add(page_link)
    db.session.commit()
    print(f"✅ Clinic added with Page ID: {test_page_id}")

    # 3. تجهيز الـ Agent مرة واحدة قبل الـ Loop
    agent = medical_agent(
        platform_id=1,
        clinic_id=clinic.id,
        page_id=test_page_id,
        sender_id="user_test_1",
        api_key="fw_49sCkqd3yVQTGuCL4cmEKN"
    )

    print("\n🚀 Chat started! Type 'exit' to stop.")
    print("-" * 30)

    # 4. الـ Loop اللي بتخليك تتكلم معاه باستمرار
    while True:
        user_message = input("You: ") # بيستنى تكتب رسالتك
        
        if user_message.lower() in ['exit', 'quit', 'خروج']:
            print("👋 Bye!")
            break

        try:
            print("🤖 Bot is thinking...")
            reply = agent.chat(user_message)
            print(f"✅ Bot: {reply}")
            print("-" * 30  )
            
            
        except Exception as e:
            print(f"❌ Error during chat: {e}")