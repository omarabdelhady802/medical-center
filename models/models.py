# models.py
from flask_login import UserMixin
from sqlalchemy import PrimaryKeyConstraint, ForeignKeyConstraint
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz
from notified_center import EmailSender

egypt_tz = pytz.timezone("Africa/Cairo")


db = SQLAlchemy()
# -------------------------
# Users Table
# -------------------------
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=False)


# -------------------------
# Platform Table
# -------------------------
class Platform(db.Model):
    __tablename__ = "platform"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    # Relationship to ClinicPage
    clinic_pages = db.relationship("ClinicPage", back_populates="platform")


# -------------------------
# Clinic Branch Table
# -------------------------
class ClinicBranch(db.Model):
    __tablename__ = "clinic_branch"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    services = db.Column(db.Text)     
    subservices = db.Column(db.Text)  
    note = db.Column(db.Text)  

    # Relationship to ClinicPage
    clinic_pages = db.relationship("ClinicPage", back_populates="clinic")


# -------------------------
# Clinic Page (Composite PK)
# -------------------------
class ClinicPage(db.Model):
    __tablename__ = "clinic_page"

    platform_id = db.Column(db.Integer, db.ForeignKey("platform.id"), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinic_branch.id"), nullable=False)
    page_id = db.Column(db.String(200), nullable=False)
    page_token = db.Column(db.String(500))

    __table_args__ = (
        PrimaryKeyConstraint("platform_id", "clinic_id", "page_id"),
    )

    platform = db.relationship("Platform", back_populates="clinic_pages")
    clinic = db.relationship("ClinicBranch", back_populates="clinic_pages")
    clients = db.relationship("Client", back_populates="clinic_page")


# -------------------------
# Clients (FK → Composite PK including sender_id)
# -------------------------
class Client(db.Model):
    __tablename__ = "client"

    platform_id = db.Column(db.Integer, nullable=False)
    clinic_id = db.Column(db.Integer, nullable=False)
    page_id = db.Column(db.String(200), nullable=False)
    sender_id = db.Column(db.String(200), nullable=False)

    chat_summary = db.Column(db.Text)
    expiration_date = db.Column(db.DateTime)
    last_bot_reply = db.Column(db.Text)

    __table_args__ = (
        PrimaryKeyConstraint("platform_id", "clinic_id", "page_id", "sender_id"),
        ForeignKeyConstraint(
            ["platform_id", "clinic_id", "page_id"],
            ["clinic_page.platform_id",
             "clinic_page.clinic_id",
             "clinic_page.page_id"]
        ),
    )

    clinic_page = db.relationship("ClinicPage", back_populates="clients")




# -------------------------
# Booking Table
# -------------------------
class Booking(db.Model):
    __tablename__ = "booking"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    services = db.Column(db.Text)     
    date = db.Column(db.String(100))
    phone_number = db.Column(db.String(50))
    are_recived = db.Column(db.BOOLEAN, default=False)  
    booking_time = db.Column(db.DateTime, default=datetime.now(egypt_tz))

class Patient(db.Model):
    __tablename__ = "patient"

    id = db.Column(db.Integer, primary_key=True)
    id_for_examination = db.Column(db.String(120), nullable=False)
    num_examination = db.Column(db.Integer, default=0)

DEFAULT_COUNT = 3000
RESET_DAYS = 30  # reset every 30 days

class RequestCounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=DEFAULT_COUNT, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    last_reset = db.Column(db.DateTime, default=datetime.utcnow)  # track last 30-day reset

    def decrement(self):
        """Decrement counter, notify if zero, and reset if needed."""
        self.check_periodic_reset()  # reset if 30 days passed

        if self.count > 0:
            self.count -= 1

        if self.count == 0:
            self.notify()
            self.count = DEFAULT_COUNT  # reset counter after notification

        self.last_updated = datetime.utcnow()
        db.session.commit()

    def notify(self):
        """Send email notification."""
        EmailSender.EmailClient.send_email(
            subject="Billing rate",
            body="This is a reminder for exceeding the limit"
        )

    def check_periodic_reset(self):
        """Reset counter every 30 days."""
        now = datetime.utcnow()
        if now - self.last_reset >= timedelta(days=RESET_DAYS):
            self.count = DEFAULT_COUNT
            self.last_reset = now
            self.last_updated = now
            db.session.commit()