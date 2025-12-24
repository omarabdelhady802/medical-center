from flask import Flask, flash, redirect, render_template, request, url_for
import os

from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models.models import *
from models.models import db
from platforms.facebook import FacebookHandler
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


fb_handler = FacebookHandler(
    page_access_token="EAFZAh4EiZCf0cBQeYCanULFLYZAiALeDfFAVfWsjyfRgGCjBcmeNYQ04Drq3ZCN1w579LQZAhTyOJO7pIbzgrYhHuB6dtcZBQwmRG1WjcHbhcYhegtACeVZBQZC7YbasOr0ZC0SwNp65ncxZCYZCyhLCpFJn4uEuf7ZCzcdeZBz77szFanYHaRZA5iDWrQyWLUFIuZBB8pQpZAyE4gZDZD", 
    fireworks_key="fw_49sCkqd3yVQTGuCL4cmEKN"
)


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # 1. الجزء الخاص بفيسبوك (Verification) لازم يكون في الأول ومنفصل
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == "dangerMo":
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    # 2. استقبال البيانات (POST)
    data = request.get_json()
    
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            page_id = entry['id']
            for messaging_event in entry.get("messaging", []):
                
                # ✅ الفحص مكانه هنا "داخل الـ Loop" بعد ما messaging_event اتعرفت
                if 'message' not in messaging_event:
                    continue
                
                # الـ Handler هو اللي فيه فحص الـ is_echo دلوقتي
                fb_handler.handle_event(messaging_event, page_id)

    return "EVENT_RECEIVED", 200
if __name__ == "__main__":
   

    app.run(port=5000, debug=True)

