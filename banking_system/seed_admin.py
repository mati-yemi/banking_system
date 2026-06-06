"""
NeoBank - Administrative Account & Configuration Seeder

This utility script resets the database schemas (by dropping and recreating
them) and seeds the primary system administrator account alongside default system
configurations (e.g., global withdrawal limits).
"""

import os

from app import create_app
from app.extensions import db, bcrypt
from app.models import User, SystemConfig

# Admin credential defaults (override with environment variables as needed)
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@admin.com')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
ADMIN_PHONE = os.getenv('ADMIN_PHONE', None)

# Instantiate application factory
app = create_app()


def seed_database():
    """Initializes the database schema and seeds or updates the admin account."""
    with app.app_context():
        print("--------------------------------------------------")
        print("Initializing database schema...")
        db.create_all()
        
        print("Database schema ready.")
        print("Seeding or updating Administrative user...")

        # Setup primary system administrator account parameters
        email = ADMIN_EMAIL
        username = ADMIN_USERNAME
        password = ADMIN_PASSWORD
        phone = ADMIN_PHONE
        
        # Hash password using application's bcrypt instance
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        existing_admin = User.query.filter_by(email=email).first()
        if existing_admin:
            existing_admin.password = hashed_password
            existing_admin.is_admin = True
            existing_admin.username = username
            existing_admin.full_name = username
            existing_admin.phone = phone
            existing_admin.status = "Active"
            existing_admin.balance = existing_admin.balance or 1000000.0
            db.session.add(existing_admin)
            print("Existing administrative account found. Password and details updated.")
        else:
            admin_user = User(
                username=username, 
                email=email, 
                password=hashed_password, 
                balance=1000000.0, 
                is_admin=True,
                full_name=username,
                phone=phone,
                status="Active"
            )
            db.session.add(admin_user)
            print("Administrative account seeded.")
        
        print("Seeding default system configuration values...")
        config = SystemConfig.query.filter_by(key='withdrawal_limit').first()
        if not config:
            config = SystemConfig(
                key='withdrawal_limit', 
                value='1000', 
                description='Max withdrawal amount before admin approval'
            )
            db.session.add(config)
        else:
            config.value = '1000'
            config.description = 'Max withdrawal amount before admin approval'
            db.session.add(config)
        
        db.session.commit()
        
        print("--------------------------------------------------")
        print("DATABASE INITIALIZED SUCCESSFULLY!")
        print(f"Admin User Name   : {username}")
        print(f"Admin Email       : {email}")
        if existing_admin:
            print("Admin account updated successfully.")
        else:
            print(f"Account Number    : {admin_user.account_number}")
        print("System Configurations Initialized.")
        print("--------------------------------------------------")


if __name__ == "__main__":
    seed_database()
