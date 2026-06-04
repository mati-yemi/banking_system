
"""
NeoBank - Application Factory

Creates and configures the Flask application with all extensions and blueprints.
"""

import os
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from app.extensions import db, bcrypt, csrf, login_manager, migrate, limiter
from app.security import setup_audit_logger

def create_app(config_name=None):
    """
    Application factory function.
    
    Args:
        config_name: Configuration class name ('DevelopmentConfig', 'ProductionConfig', 'TestingConfig')
                    If None, uses FLASK_ENV environment variable.
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration from environment
    env = os.getenv('FLASK_ENV', 'development').lower()
    if config_name is None:
        if env == 'production':
            from config import ProductionConfig
            config_name = ProductionConfig
        elif env == 'testing':
            from config import TestingConfig
            config_name = TestingConfig
        else:
            from config import DevelopmentConfig
            config_name = DevelopmentConfig
    
    app.config.from_object(config_name)

    if env == 'production' and hasattr(config_name, 'validate'):
        config_name.validate()

    # Fallback to SQLite during development if configured database is unavailable
    if env != 'production':
        database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if database_uri.startswith(('postgresql://', 'postgres://')):
            try:
                create_engine(database_uri).connect().close()
            except OperationalError as exc:
                from config import DEFAULT_DB_PATH
                os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)
                fallback_uri = f"sqlite:///{DEFAULT_DB_PATH}"
                print(f"Warning: Could not connect to configured database. Falling back to SQLite at {fallback_uri}.")
                print(f"Database error: {exc}")
                app.config['SQLALCHEMY_DATABASE_URI'] = fallback_uri
                app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    
    # Setup audit logging
    with app.app_context():
        setup_audit_logger()
    
    # Register security headers middleware
    @app.after_request
    def set_security_headers(response):
        """Apply security headers to all responses."""
        security_headers = app.config.get('SECURITY_HEADERS', {})
        for header, value in security_headers.items():
            response.headers[header] = value
        return response
    
    # Register error handlers
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden access."""
        return {'error': 'Access Forbidden'}, 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found."""
        return {'error': 'Page Not Found'}, 404
    
    @app.errorhandler(500)
    def server_error(error):
        """Handle server errors."""
        db.session.rollback()
        return {'error': 'Internal Server Error'}, 500
    
    # Register blueprints
    from app.auth.routes import auth
    from app.banking.routes import banking
    from app.admin.routes import admin
    
    app.register_blueprint(auth)
    app.register_blueprint(banking)
    app.register_blueprint(admin)
    
    # Create database tables
    with app.app_context():
        db.create_all()

    # Inject pending transaction count into all templates to avoid undefined errors
    @app.context_processor
    def inject_pending_tx_count():
        try:
            from flask_login import current_user
            from app.models import Transaction

            if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
                count = Transaction.query.filter_by(status='Pending').count()
            else:
                count = 0
        except Exception:
            count = 0
        return dict(pending_tx_count=count)
    
    return app