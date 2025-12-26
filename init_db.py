"""
Database initialization script
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Delivery

def init_database():
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created")
        
        # Check if we need sample data
        if User.query.count() == 0:
            # Create sample drivers
            sample_drivers = [
                User(
                    id="driver_001",
                    phone="250788123456",
                    name="John Doe",
                    vehicle_type="motorcycle",
                    license_plate="RAA123A"
                ),
                User(
                    id="driver_002",
                    phone="250789654321",
                    name="Jane Smith",
                    vehicle_type="car",
                    license_plate="RAB456B"
                )
            ]
            
            for driver in sample_drivers:
                driver.set_password("password123")
                db.session.add(driver)
            
            db.session.commit()
            print("✅ Sample drivers created")
        
        print("✅ Database initialization complete!")
        print(f"📊 Total drivers: {User.query.count()}")
        print(f"📊 Total delivery sessions: {Delivery.query.count()}")

if __name__ == '__main__':
    init_database()