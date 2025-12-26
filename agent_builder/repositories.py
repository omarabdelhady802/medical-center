from models.models import ClinicPage, ClinicBranch, Client, db
from sqlalchemy.exc import IntegrityError




class ClinicRepository:
    @staticmethod
    def get_by_page_id(page_id):
        """
        Efficiently gets the Branch by searching for the Page ID.
        Uses a JOIN so you don't have to query the database twice.
        """
        return db.session.query(ClinicBranch)\
            .join(ClinicPage, ClinicBranch.id == ClinicPage.clinic_id)\
            .filter(ClinicPage.page_id == page_id)\
            .first()
    
    @staticmethod
    def get_by_id(clinic_id):
        """Modern SQLAlchemy syntax for fetching by ID"""
        return db.session.get(ClinicBranch, clinic_id)

class ClientRepository:
    @staticmethod
    def get_or_create(platform_id, clinic_id, page_id, sender_id):
        """
        Handles the complex composite key for the Client.
        """
        # 1. Try to find the client first
        client = Client.query.filter_by(
            platform_id=platform_id,
            sender_id=sender_id,
            page_id=page_id # Added page_id for extra safety with your composite key
        ).first()
        
        # 2. If not found, create them
        if not client:
            try:
                client = Client(
                    platform_id=platform_id,
                    clinic_id=clinic_id,
                    page_id=page_id,
                    sender_id=sender_id,
                    last_bot_reply="",
                    chat_summary="",
                    expiration_date=None
                )
                db.session.add(client)
                db.session.commit()
            except IntegrityError:
                # Rollback in case of a race condition (two messages at once)
                db.session.rollback()
                # Try fetching one last time
                client = Client.query.filter_by(
                    platform_id=platform_id,
                    sender_id=sender_id,
                    page_id=page_id
                ).first()
        
        return client