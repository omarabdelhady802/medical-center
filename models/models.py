# models.py
from flask_login import UserMixin
from sqlalchemy import PrimaryKeyConstraint, ForeignKeyConstraint
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

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
    booking_time = db.Column(db.DateTime, default=datetime.now(egypt_tz))