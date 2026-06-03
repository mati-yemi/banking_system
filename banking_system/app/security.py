"""
NeoBank - Security Utilities

This module provides security-related utilities including audit logging,
input validation, and security decorators.
"""

import logging
import os
import re
import hashlib
from datetime import datetime
from functools import wraps
from flask import request, current_app, session
from bleach import clean as bleach_clean

# Configure audit logger
def setup_audit_logger():
    """Setup audit logging for security events."""
    audit_log_enabled = current_app.config.get('AUDIT_LOG_ENABLED', True)
    audit_log_file = current_app.config.get('AUDIT_LOG_FILE', 'logs/audit.log')
    
    if not audit_log_enabled:
        return None
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(audit_log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(audit_log_file)
    file_handler.setLevel(logging.INFO)
    
    # Formatter with timestamp and details
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    if not audit_logger.handlers:
        audit_logger.addHandler(file_handler)
    
    return audit_logger


def log_security_event(event_type, user_id=None, username=None, details=None, severity='INFO'):
    """
    Log security events to audit log.
    
    Args:
        event_type: Type of security event (e.g., 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'UNAUTHORIZED_ACCESS')
        user_id: ID of the user involved
        username: Username of the user involved
        details: Additional details about the event
        severity: Log severity level (INFO, WARNING, CRITICAL)
    """
    try:
        audit_logger = setup_audit_logger()
        if not audit_logger:
            return
        
        ip_address = request.remote_addr if request else 'UNKNOWN'
        user_info = f"User: {username or 'Anonymous'} (ID: {user_id or 'N/A'})"
        event_details = f" | {details}" if details else ""
        
        message = f"{event_type} | {user_info} | IP: {ip_address}{event_details}"
        
        log_method = getattr(audit_logger, severity.lower(), audit_logger.info)
        log_method(message)
    except Exception as e:
        # Log failure silently to avoid disrupting application
        print(f"Error logging security event: {e}")


# ===== INPUT VALIDATION =====

def validate_password_strength(password):
    """
    Validate password meets security requirements.
    
    Returns: (is_valid, error_message)
    """
    min_length = current_app.config.get('PASSWORD_MIN_LENGTH', 12)
    require_uppercase = current_app.config.get('PASSWORD_REQUIRE_UPPERCASE', True)
    require_lowercase = current_app.config.get('PASSWORD_REQUIRE_LOWERCASE', True)
    require_digits = current_app.config.get('PASSWORD_REQUIRE_DIGITS', True)
    require_special = current_app.config.get('PASSWORD_REQUIRE_SPECIAL', True)
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long."
    
    if require_uppercase and not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    
    if require_lowercase and not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    
    if require_digits and not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit."
    
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    
    return True, ""


def sanitize_input(user_input, max_length=255):
    """
    Sanitize user input to prevent XSS attacks.
    
    Returns: Sanitized string
    """
    if not isinstance(user_input, str):
        return str(user_input)[:max_length]
    
    # Remove HTML tags and dangerous content
    sanitized = bleach_clean(
        user_input,
        tags=[],  # No HTML tags allowed
        strip=True
    )
    
    return sanitized[:max_length]


def validate_amount(amount_str):
    """
    Validate financial amounts.
    
    Returns: (is_valid, value_or_error_message)
    """
    try:
        amount = float(amount_str)
        
        # Prevent negative amounts
        if amount <= 0:
            return False, "Amount must be greater than zero."
        
        # Prevent extremely large amounts (more than 1 billion)
        if amount > 1_000_000_000:
            return False, "Amount exceeds maximum allowed transaction limit."
        
        # Check decimal places (max 2)
        if len(str(amount).split('.')[-1]) > 2:
            return False, "Amount can have maximum 2 decimal places."
        
        return True, amount
    except (ValueError, TypeError):
        return False, "Invalid amount format."


# ===== SECURITY DECORATORS =====

def require_https(f):
    """Decorator to enforce HTTPS in production."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config.get('PREFERRED_URL_SCHEME') == 'https' and not current_app.config.get('DEBUG'):
            if not request.is_secure:
                log_security_event('INSECURE_REQUEST', details=f'Non-HTTPS request to {request.path}', severity='WARNING')
                return {'error': 'HTTPS required'}, 403
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_login(f):
    """Decorator for rate limiting login attempts."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            ip_address = request.remote_addr
            session_key = f'login_attempts_{ip_address}'
            
            attempts = session.get(session_key, 0)
            limit = current_app.config.get('LOGIN_ATTEMPTS_LIMIT', 5)
            
            if attempts >= limit:
                log_security_event(
                    'BRUTE_FORCE_ATTEMPT',
                    details=f'Too many login attempts from {ip_address}',
                    severity='CRITICAL'
                )
                return {'error': 'Too many login attempts. Please try again later.'}, 429
            
            session[session_key] = attempts + 1
            session.permanent = True
        
        return f(*args, **kwargs)
    return decorated_function


def hash_data(data):
    """
    Hash sensitive data using SHA-256.
    
    Returns: Hexadecimal hash string
    """
    return hashlib.sha256(str(data).encode()).hexdigest()


def constant_time_compare(a, b):
    """
    Compare two strings in constant time to prevent timing attacks.
    
    Returns: True if strings are equal, False otherwise
    """
    return hashlib.pbkdf2_hmac('sha256', a.encode(), b'salt', 100000) == hashlib.pbkdf2_hmac('sha256', b.encode(), b'salt', 100000)
