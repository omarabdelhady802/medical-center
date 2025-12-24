from models.models import ClinicPage, ClinicBranch, Client, db

class ClinicRepository:
    @staticmethod
    def get_by_page_id(page_id):
        """
        Get clinic info by page_id
        Returns ClinicBranch with all the clinic details
        """
        # First find the ClinicPage
        clinic_page = ClinicPage.query.filter_by(page_id=page_id).first()
        
        if not clinic_page:
            return None
        
        # Then get the associated ClinicBranch
        clinic_branch = ClinicBranch.query.get(clinic_page.clinic_id)
        
        return clinic_branch
    
    @staticmethod
    def get_by_id(clinic_id):
        """Get clinic branch by ID"""
        return ClinicBranch.query.get(clinic_id)


class ClientRepository:
    @staticmethod
    def get_or_create(platform_id, clinic_id, page_id, sender_id):
        """
        Get existing client or create new one
        """
        client = Client.query.filter_by(
            platform_id=platform_id,
            sender_id=sender_id
        ).first()
        
        if not client:
            client = Client(
                platform_id=platform_id,
                clinic_id=clinic_id,
                page_id=page_id,
                sender_id=sender_id
            )
            db.session.add(client)
            db.session.commit()
        
        return client
    
    @staticmethod
    def get(sender_id):
        """Get client by sender ID"""
        return Client.query.filter_by(sender_id=sender_id).first()
