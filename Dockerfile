# استخدام نسخة مستقرة وخفيفة
FROM python:3.11-slim-bookworm

# تثبيت مكتبات النظام اللازمة لـ OpenCV و PyMuPDF و Flask
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# تحديد مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات أولاً لتحسين سرعة البناء (Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn  # تأكيد تثبيت gunicorn

# نسخ باقي ملفات المشروع
COPY . .

# إنشاء مجلد الـ instance لو مش موجود وضبط الصلاحيات لقاعدة البيانات
RUN mkdir -p /app/instance

# فتح البورت الخاص بالتطبيق
EXPOSE 2005

# تشغيل التطبيق باستخدام Gunicorn
# 4 workers ده رقم مناسب لمعظم السيرفرات المتوسطة
CMD ["gunicorn", "--bind", "0.0.0.0:2005", "app:app", "--workers", "4", "--timeout", "120"]