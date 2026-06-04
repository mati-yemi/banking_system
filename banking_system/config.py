"""
NeoBank - Secure Configuration

This module provides secure configuration using environment variables.
Never hardcode sensitive credentials in the code.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, 'instance', 'neobank.db')


def _normalize_database_url(url):
    if not url:
        return None
    if url.startswith('sqlite:///'):
        path = url[10:]
        if not os.path.isabs(path) and path != ':memory:':
            return f"sqlite:///{os.path.normpath(os.path.join(BASE_DIR, path))}"
    return url


class Config:
    """Base configuration with security best practices."""
    
    # ===== CRITICAL SECURITY SETTINGS =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        os.getenv('DATABASE_URL')
    ) or f'sqlite:///{DEFAULT_DB_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # ===== FLASK-LOGIN SECURITY =====
    REMEMBER_COOKIE_SECURE = os.getenv('REMEMBER_COOKIE_SECURE', 'False').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # ===== CSRF PROTECTION =====
    WTF_CSRF_ENABLED = True
    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_SSL_STRICT = os.getenv('WTF_CSRF_SSL_STRICT', 'False').lower() == 'true'
    WTF_CSRF_TIME_LIMIT = None  # CSRF token valid for session lifetime
    
    # ===== SECURITY HEADERS =====
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    }
    
    # ===== RATE LIMITING =====
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    
    # Login attempt limits: 5 attempts per 15 minutes
    LOGIN_ATTEMPTS_LIMIT = 5
    LOGIN_ATTEMPTS_TIMEOUT = 900  # 15 minutes in seconds
    
    # ===== PASSWORD REQUIREMENTS =====
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # ===== AUDIT LOGGING =====
    AUDIT_LOG_ENABLED = True
    AUDIT_LOG_FILE = os.getenv('AUDIT_LOG_FILE', 'logs/audit.log')
    
    # ===== APPLICATION SETTINGS =====
    DEBUG = False
    TESTING = False
    PREFERRED_URL_SCHEME = 'https'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration - strict security settings."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True

    @classmethod
    def validate(cls):
        """Validate production-specific configuration when production is selected."""
        if os.getenv('SECRET_KEY') in (None, '', 'dev-key-change-in-production'):
            raise ValueError("SECRET_KEY environment variable is required for production!")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_ATTEMPTS_LIMIT = 999
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False