from flask import Flask, flash, redirect, render_template, request, url_for,jsonify
import os

from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models.models import *
from models.models import db
from platforms.facebook import FacebookHandler
from platforms.waha import WAHAHandler

# Initialize Flask app
app = Flask(__name__)

# Config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///medical.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"] = False
app.config['SESSION_TYPE'] = 'filesystem'
login_manager = LoginManager(app)

# Import models after db is created
db.init_app(app)
# Create tables (does not auto-commit anything)
with app.app_context():
    db.create_all()




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


# this route for logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))





import threading # ضيف دي فوق خالص في ملف app.py

# 1️⃣ دالة المعالجة في الخلفية (دي اللي هتعمل الشغل التقيل)
def process_facebook_message(messaging_event, page_id, page_token):
    # بنفتح context جديد عشان الداتابيز تشتغل في الـ Thread الجديد
    with app.app_context():
        try:
            handler = FacebookHandler(
                page_access_token=page_token,
                fireworks_key=os.getenv("FIREWORKS_API_KEY")
            )
            handler.handle_event(messaging_event, page_id)
        except Exception as e:
            print(f"❌ Error in background process: {e}")

# 2️⃣ الـ Webhook Route (بقى وظيفته الاستلام والرد السريع بس)
@app.route("/fb_webhook", methods=["GET", "POST"])
def fb_webhook():
    if request.method == "GET":
        # كود الـ Verification (زي ما هو)
        if request.args.get("hub.verify_token") == "dangerMo":
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    payload = request.json
    for event in payload.get("entry", []):
        page_id = event.get("id")
        
        # بنجيب التوكن بسرعة ونخرج
        page_data = ClinicPage.query.filter_by(page_id=str(page_id)).first()
        if not page_data: continue

        for messaging_event in event.get("messaging", []):
            if 'message' in messaging_event and not messaging_event.get('message').get('is_echo'):
                
                # 🔥 هنا السحر: بنشغل المعالجة في "Thread" منفصل
                # ونقوله خد الرسالة دي وعالجها مع نفسك أنا هرد على فيسبوك دلوقتي
                thread = threading.Thread(
                    target=process_facebook_message, 
                    args=(messaging_event, page_id, page_data.page_token)
                )
                thread.start() # ابدأ المعالجة بعيد عن الـ Route

    # 3️⃣ بنرد على فيسبوك فوراً (غالباً في أقل من 100 مللي ثانية)
    # كده فيسبوك مستحيل يبعت الرسالة تاني لأنك رديت عليه بسرعة البرق
    return jsonify({"status": "ok"}), 200

# WAHA instances config
WAHA_INSTANCES = {
    "INSTANCE_1": {
        "api_url": os.getenv("WAHA_API_URL"),
        "instance": os.getenv("WAHA_INSTANCE_1"),
        "api_key": os.getenv("WAHA_API_KEY_1")
    },
    "INSTANCE_2": {
        "api_url": os.getenv("WAHA_API_URL"),
        "instance": os.getenv("WAHA_INSTANCE_2"),
        "api_key": os.getenv("WAHA_API_KEY_2")
    }
}

# create handler cache لكل instance
waha_handlers = {}
for name, cfg in WAHA_INSTANCES.items():
    waha_handlers[name] = WAHAHandler(cfg["api_url"], cfg["instance"], cfg["api_key"])

# single webhook route لكل WAHA
@app.route("/waha_webhook", methods=["POST"])
def waha_webhook():
    payload = request.json
    instance_name = payload.get("instance_name")  # from webhook
    handler = waha_handlers.get(instance_name)
    if not handler:
        return jsonify({"status": "ignored", "reason": "unknown instance"}), 400

    result = handler.handle_payload(payload)
    return jsonify(result or {"status": "ok"}), 200

if __name__ == "__main__":
   

    app.run(port=5000, debug=True)

