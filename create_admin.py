import logging
from app import create_app, db
from models import Admin
from werkzeug.security import generate_password_hash

def init_admin():
    app = create_app()
    with app.app_context():
        # 1. Create tables if they don't exist
        db.create_all()
        
        # 2. Check if admin already exists
        admin_email = "admin@connection.rw"
        existing_admin = Admin.query.filter_by(email=admin_email).first()
        
        if not existing_admin:
            logging.info("Creating default admin account...")
            admin = Admin(
                username="admin",
                email=admin_email,
                password_hash=generate_password_hash("YourSecurePassword123")
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin created successfully!")
        else:
            print("ℹ️ Admin already exists, skipping creation.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_admin()