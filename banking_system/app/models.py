"""
NeoBank - Database Schemas & Models

This module defines the database models representing key entities of the NeoBank ecosystem,
including Users, Ledger Transactions, Support Messages, and System Configuration Parameters.
"""

import secrets
import string
from datetime import datetime
from flask_login import UserMixin

from app.extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the database by primary key. Required by Flask-Login."""
    return User.query.get(int(user_id))


def generate_account_number():
    """
    Generates a cryptographically secure, unique 10-digit account number.
    Uses secrets module for cryptographic randomness instead of random.
    """
    # Loop until a unique account number is produced
    while True:
        # Use secrets for cryptographic randomness
        acct = ''.join(secrets.choice(string.digits) for _ in range(10))
        try:
            # If the database is not yet initialized, this will raise; then accept the value
            existing = User.query.filter_by(account_number=acct).first()
        except Exception:
            return acct
        if not existing:
            return acct


class User(db.Model, UserMixin):
    """User database model representing NeoBank clients and administrators."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    account_number = db.Column(
        db.String(10), 
        unique=True, 
        nullable=False, 
        default=generate_account_number
    )
    balance = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
    
    # User status: 'Active' indicates a healthy account, 'Suspended' disables transfers/withdrawals
    status = db.Column(db.String(20), default='Active')
    
    # Account security fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Back-reference linking a client to all their transactions
    transactions = db.relationship('Transaction', backref='owner', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Balance: {self.balance}, Status: {self.status})"


class Transaction(db.Model):
    """Transaction database model representing a financial ledger entry."""

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    
    # Transaction type: 'deposit', 'withdrawal', 'transfer_in', or 'transfer_out'
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(100), nullable=True)
    
    # Ledger status: 'Pending' (needs approval), 'Completed' (finalized), 'Rejected' (cancelled)
    status = db.Column(db.String(20), default='Completed')
    rejection_reason = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Audit trail
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Transaction('{self.type}', Amount: {self.amount}, Status: {self.status})"


class SystemConfig(db.Model):
    """SystemConfig database model representing dynamic environment configurations."""

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"SystemConfig('{self.key}', '{self.value}')"


class SupportMessage(db.Model):
    """SupportMessage database model representing client-to-admin communication channels."""

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Recipient ID can be null if directed towards the general system admin pool
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

    def __repr__(self):
        return f"SupportMessage('{self.subject}', From: {self.sender.username})"
