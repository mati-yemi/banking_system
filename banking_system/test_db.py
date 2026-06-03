"""
NeoBank - Database Connectivity Test Script

Utility script to verify connection to the configured database and ensure all
database schemas can be created successfully in the current application context.
"""

from app import create_app
from app.extensions import db

# Create application instance using config parameters
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        print("--------------------------------------------------")
        print("Verifying Database Connection...")
        print("Connected to:", app.config["SQLALCHEMY_DATABASE_URI"])
        
        # Create all schemas defined in models
        db.create_all()
        print("SUCCESS: Database tables initialized successfully.")
        print("--------------------------------------------------")