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

# Instantiate application factory
app = create_app()


def seed_database():
    """Resets the database schema and seeds initial configurations and admin user."""
    with app.app_context():
        print("--------------------------------------------------")
        print("WARNING: Re-initializing Database...")
        print("Recreating database schema (dropping any existing tables)...")
        db.drop_all()
        db.create_all()
        
        print("Database schemas created successfully.")
        print("Seeding Administrative user...")

        # Setup primary system administrator account parameters
        email = "matiyem71@gmail.com"
        username = "MATI YEMI ANGELE"
        password = "Admin@SecureNeoBank2024!"  # Meets security requirements: 12+ chars, uppercase, lowercase, digits, special
        
        # Hash password using application's bcrypt instance
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        admin_user = User(
            username=username, 
            email=email, 
            password=hashed_password, 
            balance=1000000.0, 
            is_admin=True,
            full_name="MATI YEMI ANGELE",
            phone="677069634",
            status="Active"
        )
        db.session.add(admin_user)
        
        print("Seeding default system configuration values...")
        # Define withdrawal limit parameter: requires admin confirmation for values > $1000
        config = SystemConfig(
            key='withdrawal_limit', 
            value='1000', 
            description='Max withdrawal amount before admin approval'
        )
        db.session.add(config)
        
        # Commit session changes to persistence store
        db.session.commit()
        
        print("--------------------------------------------------")
        print("DATABASE INITIALIZED SUCCESSFULLY!")
        print(f"Admin User Name   : {username}")
        print(f"Admin Email       : {email}")
        print(f"Account Number    : {admin_user.account_number}")
        print("System Configurations Initialized.")
        print("--------------------------------------------------")


if __name__ == "__main__":
    seed_database()
