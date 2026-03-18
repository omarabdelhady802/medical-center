from flask import Flask, flash, redirect, render_template, request, url_for,jsonify
import os
import threading
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models.models import *
from models.models import db
from platforms.facebook import FacebookHandler
from platforms.waha import WAHAHandler
from parsers.facebook  import parse_facebook_message
from parsers.waha import parse_waha_message
from service.message_processor import process_message
from concurrent.futures import ThreadPoolExecutor
from notified_center.EmailSender import EmailClient
email_client = EmailClient()



# Initialize Flask app
app = Flask(__name__)

# Config
basedir = os.path.abspath(os.path.dirname(__file__))


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "instance", "medical.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"] = False
app.config['SESSION_TYPE'] = 'filesystem'

login_manager = LoginManager(app)

# Import models after db is created
db.init_app(app)
migrate = Migrate(app, db)   # ✅ مهم جدًا

with app.app_context():
    db.create_all()  # create tables if not exist
    if not RequestCounter.query.first():
        counter = RequestCounter(count=3000)
        db.session.add(counter)
        db.session.commit()




@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




#login page
@app.route('/',methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("platforms"))
    if request.method == 'POST':
        username =request.form.get('username')
        password =request.form.get('password')
        
        user = User.query.filter_by(name=username, password=password).first()
        

        if user:
            login_user(user)
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('platforms'))
        else:
            flash('اسم المستخدم او كلمه المرور غير صحيحه', 'danger')
    return render_template('index.html')



# start of platforms routes

# this route for display platforms 
@app.route('/platforms')
@login_required
def platforms():
    platforms_list = Platform.query.all()
    
    return render_template("platforms.html",platforms_list = platforms_list) 

#this route for add new platform
@app.route('/platforms/new', methods=['GET', 'POST'])
@login_required
def new_platform():
    if request.method == 'POST':
        name = request.form.get('name')
        platform = Platform.query.filter(Platform.name == name).first()
        if platform :
            flash("هذا الاسم موجود بالفعل","danger")
        else:    
            new_platform = Platform(name=name)
            db.session.add(new_platform)
            db.session.commit()
        return redirect(url_for('platforms'))

    return render_template('new_platform.html')

# this route for edit platform info
@app.route('/platforms/edit/<int:platform_id>', methods=['GET', 'POST'])
@login_required
def edit_platform(platform_id):
    platform = Platform.query.get_or_404(platform_id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        name_validation = Platform.query.filter(Platform.name == new_name).first()
        if new_name == platform.name :
            db.session.commit()
            return redirect(url_for('platforms'))
        else :    
            if name_validation:
                flash("هذا الاسم موجود بالفعل","danger")
                return redirect(url_for('platforms'))
            else :
                platform.name = request.form.get('name')
                db.session.commit()
                return redirect(url_for('platforms'))

    return render_template('edit_platform.html', platform=platform)


# start of users routes
# this route for display users
@app.route('/users')
@login_required
def users():
    users_list = User.query.all()

    return render_template('users.html', users=users_list)

# this route for add new user in db
@app.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    if request.method == 'POST':
        name = request.form.get('name')
        user = User.query.filter(User.name == name).first()
        password = request.form.get('password')
        if user :
            flash("هذا الاسم موجود بالفعل","danger")
        else:    
            new_user = User(name=name , password = password )
            db.session.add(new_user)
            db.session.commit()
        return redirect(url_for('users'))

    return render_template('new_user.html')


#this route for edit user
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        name_validation = User.query.filter(User.name == new_name).first()
        if new_name == user.name :
            user.password = request.form.get('password')
            db.session.commit()
            return redirect(url_for('users'))
        else :    
            if name_validation:
                flash("هذا الاسم موجود بالفعل","danger")
                return redirect(url_for('users'))
            else :
                db.session.rollback()
                user.name = request.form.get('name')
                user.password = request.form.get('password')
                db.session.commit()
                return redirect(url_for('users'))

    return render_template('edit_user.html', user=user)
# end of users routes



# -----------------------------------------
# CLINIC BRANCH ROUTES
# -----------------------------------------

@app.route('/clinics')
@login_required
def clinics():
    clinics_list = ClinicBranch.query.all()
    return render_template('clinics.html', clinics=clinics_list)


@app.route('/clinics/new', methods=['GET', 'POST'])
@login_required
def new_clinic():
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        services = request.form.get('services')
        subservices = request.form.get('subservices')

        # Prevent duplicate clinic names
        existing = ClinicBranch.query.filter(ClinicBranch.name == name).first()
        if existing:
            flash("هذا الاسم موجود بالفعل", "danger")
            return redirect(url_for('clinics'))

        clinic = ClinicBranch(
            name=name,
            address=address,
            services=services,
            subservices=subservices
        )
        db.session.add(clinic)
        db.session.commit()
        return redirect(url_for('clinics'))

    return render_template('new_clinic.html')


@app.route('/clinics/edit/<int:clinic_id>', methods=['GET', 'POST'])
@login_required
def edit_clinic(clinic_id):
    clinic = ClinicBranch.query.get_or_404(clinic_id)

    if request.method == 'POST':
        new_name = request.form.get('name')
        address = request.form.get('address')
        services = request.form.get('services')
        subservices = request.form.get('subservices')

        validation = ClinicBranch.query.filter(ClinicBranch.name == new_name).first()

        if new_name == clinic.name:
            clinic.address = address
            clinic.services = services
            clinic.subservices = subservices
            db.session.commit()
            return redirect(url_for('clinics'))
        else:
            if validation:
                flash("هذا الاسم موجود بالفعل", "danger")
                return redirect(url_for('clinics'))
            else:
                clinic.name = new_name
                clinic.address = address
                clinic.services = services
                clinic.subservices = subservices
                db.session.commit()
                return redirect(url_for('clinics'))

    return render_template('edit_clinic.html', clinic=clinic)



# -----------------------------------------
# CLINIC PAGE ROUTES
# -----------------------------------------

@app.route('/clinic-pages')
@login_required
def clinic_pages():
    pages = ClinicPage.query.all()
    return render_template('clinic_pages.html', pages=pages)


@app.route('/clinic-pages/new', methods=['GET', 'POST'])
@login_required
def new_clinic_page():
    clinics = ClinicBranch.query.all()
    platforms = Platform.query.all()

    if request.method == 'POST':
        platform_id = request.form.get('platform_id')
        clinic_id = request.form.get('clinic_id')
        page_id = request.form.get('page_id')
        page_token = request.form.get('page_token')

        # Composite key check
        exists = ClinicPage.query.filter_by(
            platform_id=platform_id,
            clinic_id=clinic_id,
            page_id=page_id
        ).first()

        if exists:
            flash("هذه الصفحة موجوده بالفعل لهذا الفرع", "danger")
            return redirect(url_for('clinic_pages'))

        new_page = ClinicPage(
            platform_id=platform_id,
            clinic_id=clinic_id,
            page_id=page_id,
            page_token=page_token
        )

        db.session.add(new_page)
        db.session.commit()
        return redirect(url_for('clinic_pages'))

    return render_template('new_clinic_page.html', clinics=clinics, platforms=platforms)

@app.route('/clinic-pages/delete/<int:platform_id>/<int:clinic_id>/<path:page_id>', methods=['POST'])
@login_required
def delete_clinic_page(platform_id, clinic_id, page_id):
    page = ClinicPage.query.get_or_404((platform_id, clinic_id, page_id))

    db.session.delete(page)
    db.session.commit()

    flash("تم حذف الصفحة بنجاح", "success")
    return redirect(url_for('clinic_pages'))

@app.route('/booking')
@login_required
def booking():
    books = Booking.query.all()
    return render_template('booking.html', books=books)


# this route for logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))






# ✅ استخدام ThreadPoolExecutor بدلاً من threading مباشرة
# يدير الـ threads بشكل أفضل ويمنع التراكم
executor = ThreadPoolExecutor(max_workers=10)


# ==================== Facebook Webhook ====================

@app.route("/fb_webhook", methods=["GET", "POST"])
def fb_webhook():
    """
    Webhook للفيسبوك - يستقبل الرسائل ويعالجها
    """
    
    # 🔹 GET: التحقق من الـ Webhook (Facebook بيطلبه أول مرة)
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        VERIFY_TOKEN = "dangerMo"

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("[INFO] Facebook Webhook verified successfully!")
            return challenge, 200
        
        print("[WARNING] Facebook Webhook verification failed")
        return "Forbidden", 403

    # 🔹 POST: استقبال الرسائل
    try:
        payload = request.json
        
        if not payload:
            return jsonify({"status": "no_payload"}), 200

        for entry in payload.get("entry", []):
            page_id = entry.get("id")

            for ev in entry.get("messaging", []):
                # تجاهل الرسائل الصادرة والـ delivery receipts
                if (
                    ev.get("message", {}).get("is_echo")
                    or "delivery" in ev
                    or "read" in ev
                    or "reaction" in ev
                ):
                    continue

                # تحليل الرسالة
                msg = parse_facebook_message(ev)
                if not msg:
                    continue

                # ✅ معالجة الرسالة في thread منفصل
                def process_fb_message(captured_msg=msg,captured_page_id=page_id):
                    try:
                        with app.app_context():
                            process_message(FacebookHandler, 1, captured_page_id,captured_msg)
                    except Exception as e:
                        print(f"[ERROR] Facebook message processing failed: {e}")
                        import traceback
                        traceback.print_exc()

                # استخدام ThreadPoolExecutor بدلاً من threading.Thread
                executor.submit(process_fb_message)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"[ERROR] Facebook webhook error: {e}")
        email_client.send_email(
            subject="Facebook Webhook Error in app file",
            body=f"An error occurred in Facebook webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ==================== WAHA Webhook ====================

@app.route("/waha_webhook", methods=["POST"])
def waha_webhook():
    """
    Webhook لواتساب (WAHA) - يستقبل الرسائل ويعالجها
    """
    try:
        data = request.json
        print(f"--- Received Message: {data} ---") #
        
        if not data:
            return jsonify({"status": "no_data"}), 200

        payload = data.get("payload", {})
        
        # تجاهل الرسائل الصادرة منك
        if payload.get("fromMe") is True:
            return jsonify({"status": "ignored_outgoing"}), 200

        # تحليل الرسالة
        msg = parse_waha_message(payload)
        if not msg:
            return jsonify({"status": "no_message"}), 200
        
        # استخراج معرف البوت (رقم التليفون)
        bot_phone_id = data.get("me", {}).get("id")
        
        if not bot_phone_id:
            print("[WARNING] No bot phone ID in WAHA webhook")
            return jsonify({"status": "no_bot_id"}), 200

        # ✅ معالجة الرسالة في thread منفصل
        def process_waha_message(captured_msg=msg,captured_bot_id=bot_phone_id):
            try:
                with app.app_context():
                    process_message(WAHAHandler, 2, captured_bot_id, captured_msg)
            except Exception as e:
                print(f"[ERROR] WAHA message processing failed: {e}")
                import traceback
                traceback.print_exc()

        # استخدام ThreadPoolExecutor
        executor.submit(process_waha_message)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"[ERROR] WAHA webhook error: {e}")
        email_client.send_email(
            subject="WAHA Webhook Error in app file",
            body=f"An error occurred in WAHA webhook: {e}"
        )
        
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ==================== Health Check ====================

@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint - للتأكد إن السيرفر شغال
    """
    return jsonify({
        "status": "healthy",
        "active_threads": threading.active_count()
    }), 200


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    patients = []

    if request.method == 'POST':
        search_term = request.form.get('id_for_examination')
        
        if search_term:
            # Partial match search using SQLAlchemy `like`
            patients = Patient.query.filter(
                Patient.id_for_examination.like(f"%{search_term}%")
            ).all()

            if not patients:
                flash("لا يوجد مرضى مطابقون", "danger")
        else:
            flash("ادخل قيمة للبحث", "warning")

    return render_template('dashboard.html', patients=patients)


@app.route('/update_patient/<int:patient_id>', methods=['POST'])
def update_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    try:
        new_value = int(request.form.get('num_examination'))
        if new_value < 0:
            flash("القيمة لا يمكن أن تكون سالبة", "danger")
        else:
            patient.num_examination = new_value
            db.session.commit()
            flash("تم التحديث بنجاح ✅", "success")
    except:
        flash("خطأ في الإدخال ❌", "danger")

    return redirect(url_for('dashboard'))


# --- Add new patient ---
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        exam_id = request.form.get('id_for_examination')

        # Prevent duplicates
        existing_patient = Patient.query.filter_by(id_for_examination=exam_id).first()
        if existing_patient:
            flash("هذا المريض موجود بالفعل", "danger")
            return redirect(url_for('add_patient'))

        try:
            new_patient = Patient(
                id_for_examination=exam_id,
                num_examination=0
            )
            db.session.add(new_patient)
            db.session.commit()
            flash("تم إضافة المريض بنجاح ✅", "success")
            return redirect(url_for('dashboard'))
        except:
            flash("حدث خطأ أثناء الإضافة ❌", "danger")

    return render_template('add_patient.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=2005, threaded=True)
