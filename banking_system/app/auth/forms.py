"""
NeoBank - Authentication Forms

This module defines Flask-WTF input validation forms for customer actions,
such as registration and login credentials checks.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional

from app.models import User
from app.security import validate_password_strength, sanitize_input


class RegistrationForm(FlaskForm):
    """Registration form mapping client registration fields and database validation checks."""

    username = StringField(
        'Username', 
        validators=[DataRequired(), Length(min=3, max=20)]
    )
    email = StringField(
        'Email', 
        validators=[DataRequired(), Email()]
    )
    phone = StringField(
        'Phone',
        validators=[Optional(), Length(min=7, max=20)]
    )
    password = PasswordField(
        'Password', 
        validators=[DataRequired(), Length(min=12)]
    )
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')]
    )
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        """Validates that a desired username is not already registered in the system."""
        username_value = sanitize_input(username.data)
        user = User.query.filter_by(username=username_value).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        """Validates that a desired email address is not already registered."""
        email_value = sanitize_input(email.data).lower()
        user = User.query.filter_by(email=email_value).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

    def validate_password(self, password):
        """Validates that password meets security requirements."""
        is_valid, error_msg = validate_password_strength(password.data)
        if not is_valid:
            raise ValidationError(error_msg)

    def validate_phone(self, phone):
        """Optional phone validation: ensure only digits and common separators if provided."""
        if phone.data:
            cleaned = phone.data.replace('+', '').replace('-', '').replace(' ', '')
            if not cleaned.isdigit():
                raise ValidationError('Please enter a valid phone number (digits, +, -, spaces allowed).')


class LoginForm(FlaskForm):
    """Login form for existing clients to submit authentication credentials."""

    email = StringField(
        'Email or Username', 
        validators=[DataRequired()]
    )
    password = PasswordField(
        'Password', 
        validators=[DataRequired()]
    )
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')
