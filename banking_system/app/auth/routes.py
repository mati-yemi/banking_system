"""
NeoBank - Authentication Routes

This module manages all user authentication routes, including registration,
login sessions, and secure logout with enhanced security measures.
"""

from datetime import datetime, timedelta
from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import check_password_hash
from app.extensions import db, bcrypt, limiter
from app.models import User
from app.auth.forms import RegistrationForm, LoginForm
from app.security import log_security_event, sanitize_input

# Instantiate authentication blueprint
auth = Blueprint('auth', __name__)


@auth.route("/register", methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    """
    Handles user account registration with enhanced security.
    
    - Validates form data
    - Hashes password securely using bcrypt
    - Inserts user into database
    - Logs registration event for audit trail
    """
    if current_user.is_authenticated:
        return redirect(url_for('banking.dashboard'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Sanitize inputs
            username = sanitize_input(form.username.data)
            email = sanitize_input(form.email.data).lower()
            
            # Hash the password using bcrypt
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            
            user = User(
                username=username, 
                email=email, 
                password=hashed_password,
                phone=sanitize_input(form.phone.data) if form.phone.data else None,
                created_at=datetime.utcnow(),
                password_changed_at=datetime.utcnow()
            )
            db.session.add(user)
            db.session.commit()
            
            # Log successful registration
            log_security_event('REGISTRATION_SUCCESS', user_id=user.id, username=user.username)
            
            flash('Your account has been created! You are now able to log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            log_security_event('REGISTRATION_FAILED', details=f'Registration error: {str(e)}', severity='WARNING')
            flash('An error occurred during registration. Please try again.', 'danger')
        
    return render_template('register.html', title='Register', form=form)


@auth.route("/login", methods=['GET', 'POST'])
@limiter.limit("10 per hour")  # Allow 10 login attempts per hour
def login():
    """
    Handles user authentication with enhanced security.
    
    - Authenticates user credentials
    - Implements account lockout after failed attempts
    - Establishes secure login session using Flask-Login
    - Logs authentication events for audit trail
    - Upgrades legacy password hashes to bcrypt on successful login
    """
    if current_user.is_authenticated:
        return redirect(url_for('banking.dashboard'))
        
    form = LoginForm()
    if form.validate_on_submit():
        try:
            email = sanitize_input(form.email.data).lower()
            user = User.query.filter_by(email=email).first()
            
            # Check if account is locked due to too many failed attempts
            if user and user.locked_until and user.locked_until > datetime.utcnow():
                remaining_time = (user.locked_until - datetime.utcnow()).total_seconds() / 60
                log_security_event('LOGIN_BLOCKED_LOCKED_ACCOUNT', user_id=user.id, username=user.username)
                flash(f'Account locked. Try again in {int(remaining_time)} minutes.', 'danger')
                return render_template('login.html', title='Login', form=form)
            
            # Verify password
            valid_password = False
            if user:
                try:
                    valid_password = bcrypt.check_password_hash(user.password, form.password.data)
                except ValueError:
                    # Legacy password hashes may use Werkzeug PBKDF2, fall back gracefully.
                    valid_password = check_password_hash(user.password, form.password.data)

            if user and valid_password and user.status == 'Active':
                # Reset failed login attempts on successful login
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login = datetime.utcnow()
                
                # Upgrade legacy password hashes to bcrypt on successful login
                if user.password and not user.password.startswith(('$2b$', '$2a$')):
                    user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
                    user.password_changed_at = datetime.utcnow()
                
                db.session.commit()
                
                login_user(user, remember=form.remember.data)
                log_security_event('LOGIN_SUCCESS', user_id=user.id, username=user.username, details=f'IP: {request.remote_addr}')
                
                # Retrieve the next page from arguments if redirected from a login_required guard
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('banking.dashboard'))
            else:
                # Track failed login attempts
                if user:
                    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                    
                    # Lock account after 5 failed attempts for 15 minutes
                    if user.failed_login_attempts >= 5:
                        user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                        db.session.commit()
                        log_security_event('LOGIN_ACCOUNT_LOCKED', user_id=user.id, username=user.username, severity='WARNING')
                        flash('Too many failed login attempts. Account locked for 15 minutes.', 'danger')
                    else:
                        db.session.commit()
                        log_security_event('LOGIN_FAILED', username=email, details=f'Failed attempt {user.failed_login_attempts}/5')
                
                # Generic error message to prevent username enumeration
                flash('Login Unsuccessful. Please check email and password.', 'danger')
            
        except Exception as e:
            db.session.rollback()
            log_security_event('LOGIN_ERROR', details=f'Login error: {str(e)}', severity='WARNING')
            flash('An error occurred during login. Please try again.', 'danger')
            
    return render_template('login.html', title='Login', form=form)


@auth.route("/logout")
@login_required
def logout():
    """
    Destroys the current user login session and logs the logout event.
    """
    log_security_event('LOGOUT', user_id=current_user.id, username=current_user.username)
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
