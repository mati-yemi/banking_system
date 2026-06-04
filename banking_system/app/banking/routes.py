"""
NeoBank - Customer Banking Routes

This module handles client-facing banking operations with enhanced security,
including deposits, withdrawals, transfers, transactions, and support messaging.
"""

from functools import wraps
from flask import render_template, url_for, flash, redirect, request, Blueprint, abort, jsonify
from flask_login import current_user, login_required

from app.extensions import db, limiter
from app.models import User, Transaction, SystemConfig, SupportMessage
from app.security import log_security_event, validate_amount, sanitize_input

# Instantiate banking blueprint
banking = Blueprint('banking', __name__)


def active_account_required(f):
    """Decorator to ensure that the current authenticated user's account is active.

    Suspended users are prevented from executing transactions or withdrawals.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.status == 'Suspended':
            log_security_event('SUSPENDED_ACCOUNT_ACCESS_ATTEMPT', user_id=current_user.id, username=current_user.username, severity='WARNING')
            flash('Your account has been suspended. Please contact support.', 'danger')
            return redirect(url_for('banking.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@banking.route("/")
@banking.route("/dashboard")
def dashboard():
    """Renders the customer dashboard page.

    The dashboard is now publicly accessible and will show a guest
    landing view when the user is not authenticated.
    """
    return render_template('dashboard.html', title='Dashboard')


@banking.route("/deposit", methods=['GET', 'POST'])
@login_required
@active_account_required
@limiter.limit("20 per hour")
def deposit():
    """
    Handles manual customer balance deposits with validation and audit logging.
    
    - Validates numeric amount
    - Prevents negative or excessive amounts
    - Logs transaction for audit trail
    """
    if request.method == 'POST':
        try:
            amount_str = request.form.get('amount', '').strip()
            is_valid, amount_or_error = validate_amount(amount_str)
            
            if is_valid:
                amount = amount_or_error
                current_user.balance += amount
                transaction = Transaction(
                    amount=amount, 
                    type='deposit', 
                    description='Deposit', 
                    user_id=current_user.id
                )
                db.session.add(transaction)
                db.session.commit()
                
                log_security_event('DEPOSIT_SUCCESS', user_id=current_user.id, username=current_user.username, 
                                 details=f'Amount: ${amount:.2f}')
                flash(f'Successfully deposited ${amount:.2f}', 'success')
                return redirect(url_for('banking.dashboard'))
            else:
                log_security_event('INVALID_DEPOSIT_ATTEMPT', user_id=current_user.id, username=current_user.username, 
                                 details=f'Reason: {amount_or_error}', severity='WARNING')
                flash(amount_or_error, 'danger')
        except Exception as e:
            db.session.rollback()
            log_security_event('DEPOSIT_ERROR', user_id=current_user.id, username=current_user.username, 
                             details=f'Error: {str(e)}', severity='WARNING')
            flash('An error occurred during deposit. Please try again.', 'danger')
            
    return render_template('deposit.html', title='Deposit')


@banking.route("/withdraw", methods=['GET', 'POST'])
@login_required
@active_account_required
@limiter.limit("20 per hour")
def withdraw():
    """
    Handles manual customer balance withdrawals with limits and approval workflows.
    
    - Large withdrawals exceeding the global limit require administrative approval
    - Regular users have their funds deducted and held in a 'Pending' status
    - Admins are exempt from approval limits
    - All attempts are logged for audit trail
    """
    if request.method == 'POST':
        try:
            amount_str = request.form.get('amount', '').strip()
            is_valid, amount_or_error = validate_amount(amount_str)
            
            if is_valid:
                amount = amount_or_error
                
                if amount > current_user.balance:
                    log_security_event('INSUFFICIENT_FUNDS_WITHDRAWAL', user_id=current_user.id, 
                                     username=current_user.username, details=f'Requested: ${amount:.2f}, Balance: ${current_user.balance:.2f}')
                    flash('Insufficient funds', 'danger')
                    return render_template('withdraw.html', title='Withdraw')
                
                # Retrieve the configured system withdrawal approval threshold
                config = SystemConfig.query.filter_by(key='withdrawal_limit').first()
                limit = float(config.value) if config else 1000.0
                
                if amount > limit and not current_user.is_admin:
                    # Deduct balance immediately and create a Pending approval transaction
                    current_user.balance -= amount
                    transaction = Transaction(
                        amount=amount, 
                        type='withdrawal', 
                        description='Withdrawal (Pending Admin Approval)', 
                        status='Pending', 
                        user_id=current_user.id
                    )
                    db.session.add(transaction)
                    db.session.commit()
                    
                    log_security_event('WITHDRAWAL_PENDING_APPROVAL', user_id=current_user.id, 
                                     username=current_user.username, details=f'Amount: ${amount:.2f} (exceeds limit: ${limit:.2f})')
                    flash(f'Withdrawal of ${amount:.2f} is pending administrative approval.', 'warning')
                    return redirect(url_for('banking.dashboard'))
                else:
                    # Immediate completion for admins or transactions within limits
                    current_user.balance -= amount
                    transaction = Transaction(
                        amount=amount, 
                        type='withdrawal', 
                        description='Withdrawal', 
                        user_id=current_user.id
                    )
                    db.session.add(transaction)
                    db.session.commit()
                    
                    log_security_event('WITHDRAWAL_SUCCESS', user_id=current_user.id, 
                                     username=current_user.username, details=f'Amount: ${amount:.2f}')
                    flash(f'Successfully withdrew ${amount:.2f}', 'success')
                    return redirect(url_for('banking.dashboard'))
            else:
                log_security_event('INVALID_WITHDRAWAL_ATTEMPT', user_id=current_user.id, 
                                 username=current_user.username, details=f'Reason: {amount_or_error}', severity='WARNING')
                flash(amount_or_error, 'danger')
        except Exception as e:
            db.session.rollback()
            log_security_event('WITHDRAWAL_ERROR', user_id=current_user.id, 
                             username=current_user.username, details=f'Error: {str(e)}', severity='WARNING')
            flash('An error occurred during withdrawal. Please try again.', 'danger')
            
    return render_template('withdraw.html', title='Withdraw')


@banking.route("/transfer", methods=['GET', 'POST'])
@login_required
@active_account_required
@limiter.limit("20 per hour")
def transfer():
    """
    Handles inter-account funds transfers with validation and audit logging.
    
    - Validates recipient exists and is active
    - Prevents self-transfers
    - Creates double-entry ledger logs for accounting integrity
    - Logs all transfer attempts for audit trail
    """
    if request.method == 'POST':
        try:
            recipient_email = sanitize_input(request.form.get('email', '').strip()).lower()
            amount_str = request.form.get('amount', '').strip()
            
            # Validate amount
            is_valid, amount_or_error = validate_amount(amount_str)
            if not is_valid:
                log_security_event('INVALID_TRANSFER_AMOUNT', user_id=current_user.id, 
                                 username=current_user.username, details=f'Reason: {amount_or_error}', severity='WARNING')
                flash(amount_or_error, 'danger')
                return render_template('transfer.html', title='Transfer')
            
            amount = amount_or_error
            recipient = User.query.filter_by(email=recipient_email).first()
            
            # Validate recipient
            if not recipient:
                log_security_event('TRANSFER_RECIPIENT_NOT_FOUND', user_id=current_user.id, 
                                 username=current_user.username, details=f'Recipient email: {recipient_email}')
                flash('Recipient not found', 'danger')
            elif recipient == current_user:
                log_security_event('SELF_TRANSFER_ATTEMPT', user_id=current_user.id, 
                                 username=current_user.username, severity='WARNING')
                flash('Cannot transfer to your own account', 'danger')
            elif recipient.status == 'Suspended':
                log_security_event('TRANSFER_TO_SUSPENDED_ACCOUNT', user_id=current_user.id, 
                                 username=current_user.username, details=f'Recipient: {recipient.username}', severity='WARNING')
                flash('Recipient account is suspended and cannot receive funds.', 'danger')
            elif amount > current_user.balance:
                log_security_event('TRANSFER_INSUFFICIENT_FUNDS', user_id=current_user.id, 
                                 username=current_user.username, details=f'Requested: ${amount:.2f}, Balance: ${current_user.balance:.2f}')
                flash('Insufficient funds', 'danger')
            else:
                # Process transfer
                current_user.balance -= amount
                recipient.balance += amount
                
                # Create matching double-entry ledger logs for accounting integrity
                t1 = Transaction(
                    amount=amount, 
                    type='transfer_out', 
                    description=f'Transfer to {recipient.username}', 
                    user_id=current_user.id
                )
                t2 = Transaction(
                    amount=amount, 
                    type='transfer_in', 
                    description=f'Transfer from {current_user.username}', 
                    user_id=recipient.id
                )
                
                db.session.add_all([t1, t2])
                db.session.commit()
                
                log_security_event('TRANSFER_SUCCESS', user_id=current_user.id, 
                                 username=current_user.username, details=f'To: {recipient.username}, Amount: ${amount:.2f}')
                flash(f'Successfully transferred ${amount:.2f} to {recipient.username}', 'success')
                return redirect(url_for('banking.dashboard'))
                
        except Exception as e:
            db.session.rollback()
            log_security_event('TRANSFER_ERROR', user_id=current_user.id, 
                             username=current_user.username, details=f'Error: {str(e)}', severity='WARNING')
            flash('An error occurred during transfer. Please try again.', 'danger')
            
    return render_template('transfer.html', title='Transfer')


@banking.route("/transactions")
@login_required
def transactions():
    """Renders transaction history page listing customer-specific ledger items."""
    user_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.timestamp.desc()).all()
    return render_template('transactions.html', title='Transactions', transactions=user_transactions)


@banking.route("/support", methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per hour")
def support():
    """
    Renders customer support ticket inbox and handles new message submissions.
    
    - Sanitizes all input
    - Limits message submission rate
    - Logs all support interactions for audit trail
    """
    if request.method == 'POST':
        subject = sanitize_input(request.form.get('subject', '').strip())
        message_body = sanitize_input(request.form.get('message', '').strip())
        
        if subject and message_body and len(subject) <= 100 and len(message_body) <= 5000:
            msg = SupportMessage(
                subject=subject, 
                message=message_body, 
                sender_id=current_user.id
            )
            db.session.add(msg)
            db.session.commit()
            
            log_security_event('SUPPORT_MESSAGE_SENT', user_id=current_user.id, 
                             username=current_user.username, details=f'Subject: {subject}')
            flash('Message sent to support. We will get back to you soon.', 'success')
            return redirect(url_for('banking.support'))
        else:
            flash('Invalid message format. Please check subject and message length.', 'danger')
            
    # Retrieve messages sent by the client or replies sent specifically to them
    messages = SupportMessage.query.filter(
        (SupportMessage.sender_id == current_user.id) | 
        (SupportMessage.recipient_id == current_user.id)
    ).order_by(SupportMessage.timestamp.desc()).all()
    
    return render_template('support.html', title='Support', messages=messages)


# --- API ENDPOINTS FOR AJAX ---

@banking.route("/api/verify-recipient")
@login_required
def api_verify_recipient():
    """
    AJAX helper endpoint to verify if a target transfer recipient exists by email.
    
    - Ensures sender does not attempt to transfer funds to their own email
    - Prevents user enumeration by not disclosing if email exists
    - Returns recipient username only if it's a valid recipient
    """
    email = sanitize_input(request.args.get('email', '').strip()).lower()
    user = User.query.filter_by(email=email).first()
    
    if user and user != current_user and user.status == 'Active':
        return jsonify({"exists": True, "username": user.username})
    return jsonify({"exists": False})
