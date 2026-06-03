
"""
NeoBank - Application Factory

Creates and configures the Flask application with all extensions and blueprints.
"""

import os
from flask import Flask
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
    if config_name is None:
        env = os.getenv('FLASK_ENV', 'development').lower()
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
    
    return app