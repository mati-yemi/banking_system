"""
NeoBank - Application Extensions

This module defines and instantiates Flask extensions used globally by the
application. They are initialized inside the application factory (`create_app`).
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Database mapper using SQLAlchemy ORM
db = SQLAlchemy()

# Cryptographic password hashing wrapper
bcrypt = Bcrypt()

# Cross-Site Request Forgery (CSRF) protection helper
csrf = CSRFProtect()

# User session manager using Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Database migration helper (Alembic integration)
migrate = Migrate()

# Rate limiter for protecting against brute force and DoS attacks
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
