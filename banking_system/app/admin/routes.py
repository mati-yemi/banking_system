"""
NeoBank - Administrative Control Routes

This blueprint maps all administrative endpoints with enhanced security,
including system status summaries, user management, transaction approval,
support correspondence, and system settings.
"""

from functools import wraps
from datetime import datetime, timedelta
from flask import render_template, url_for, flash, redirect, request, Blueprint, abort, jsonify
from flask_login import current_user, login_required

from app.extensions import db, limiter
from app.models import User, Transaction, SystemConfig, SupportMessage
from app.security import log_security_event, validate_amount, sanitize_input

# Instantiate administrative blueprint with matching url prefix
admin = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator guarding route access to ensure only system administrators can execute."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            log_security_event('UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT', user_id=current_user.id if current_user.is_authenticated else None, 
                             username=current_user.username if current_user.is_authenticated else 'Anonymous', 
                             details=f'Attempted access to {request.path}', severity='CRITICAL')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Renders administrative operations dashboard with metrics and user summaries."""
    total_users = User.query.count()
    total_balance = db.session.query(db.func.sum(User.balance)).scalar() or 0.0
    
    # Retrieve pending ledger approval queue items
    pending_tx_query = Transaction.query.filter_by(status='Pending').order_by(Transaction.timestamp.desc())
    pending_count = pending_tx_query.count()
    pending_txs = pending_tx_query.limit(5).all()
    
    # Retrieve recent registrations
    users = User.query.order_by(User.id.desc()).limit(5).all()
    
    log_security_event('ADMIN_DASHBOARD_ACCESSED', user_id=current_user.id, username=current_user.username)
    
    return render_template(
        'admin/dashboard.html', 
        title='Admin Dashboard',
        total_users=total_users,
        total_balance=total_balance,
        pending_transactions=pending_count,
        pending_txs=pending_txs,
        recent_users=users
    )


@admin.route("/users")
@login_required
@admin_required
def users_list():
    """Renders administrative interface to manage system users."""
    users = User.query.all()
    log_security_event('ADMIN_USERS_LIST_ACCESSED', user_id=current_user.id, username=current_user.username)
    return render_template('admin/users.html', title='Manage Users', users=users)


@admin.route("/user/<int:user_id>/toggle-status")
@login_required
@admin_required
def toggle_user_status(user_id):
    """
    HTML redirection endpoint to suspend or activate a user account.
    
    - Prevents admin from suspending their own account
    - Logs all account status changes for audit trail
    """
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        log_security_event('SELF_SUSPENSION_ATTEMPT', user_id=current_user.id, username=current_user.username, severity='WARNING')
        flash('You cannot freeze your own account!', 'danger')
        return redirect(url_for('admin.users_list'))
    
    old_status = user.status
    user.status = 'Suspended' if user.status == 'Active' else 'Active'
    db.session.commit()
    
    log_security_event('USER_STATUS_CHANGED', user_id=current_user.id, username=current_user.username, 
                     details=f'Changed user {user.username} from {old_status} to {user.status}')
    flash(f'Account status for {user.username} updated to {user.status}.', 'success')
    return redirect(url_for('admin.users_list'))


@admin.route("/transactions")
@login_required
@admin_required
def pending_transactions():
    """Renders complete list of all transactions awaiting administrative action."""
    transactions = Transaction.query.filter_by(status='Pending').order_by(Transaction.timestamp.desc()).all()
    log_security_event('ADMIN_PENDING_TRANSACTIONS_ACCESSED', user_id=current_user.id, username=current_user.username)
    return render_template('admin/transactions.html', title='Pending Transactions', transactions=transactions)


@admin.route("/transaction/<int:transaction_id>/approve")
@login_required
@admin_required
def approve_transaction(transaction_id):
    """
    HTML redirection endpoint to confirm and finalize a pending withdrawal.
    
    - Verifies transaction is still pending
    - Checks user has sufficient balance
    - Updates transaction status to Completed
    - Logs approval with admin information
    """
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.status != 'Pending':
        log_security_event('INVALID_TRANSACTION_APPROVAL', user_id=current_user.id, username=current_user.username, 
                         details=f'Transaction {transaction_id} already processed with status: {transaction.status}', severity='WARNING')
        flash('Transaction is already processed.', 'warning')
        return redirect(url_for('admin.pending_transactions'))
    
    user = User.query.get(transaction.user_id)
    
    # Verify user has required balance for transaction completion
    if transaction.type == 'withdrawal' and user.balance < transaction.amount:
        transaction.status = 'Rejected'
        transaction.rejection_reason = 'Insufficient funds at time of approval'
        transaction.approved_by = current_user.id
        transaction.approved_at = datetime.utcnow()
        db.session.commit()
        
        log_security_event('TRANSACTION_REJECTED_INSUFFICIENT_FUNDS', user_id=current_user.id, username=current_user.username, 
                         details=f'Transaction {transaction_id}: Requested ${transaction.amount:.2f}, Available ${user.balance:.2f}')
        flash('Insufficient funds for this transaction. Rejected.', 'danger')
    else:
        # Balance was already deducted during request, simply finalize status
        transaction.status = 'Completed'
        transaction.approved_by = current_user.id
        transaction.approved_at = datetime.utcnow()
        db.session.commit()
        
        log_security_event('TRANSACTION_APPROVED', user_id=current_user.id, username=current_user.username, 
                         details=f'Transaction {transaction_id}: {transaction.type} of ${transaction.amount:.2f} for {user.username}')
        flash(f'Transaction approved for {user.username}.', 'success')
        
    return redirect(url_for('admin.pending_transactions'))


@admin.route("/transaction/<int:transaction_id>/reject")
@login_required
@admin_required
def reject_transaction(transaction_id):
    """
    HTML redirection endpoint to deny a pending withdrawal and refund held funds.
    
    - Refunds balance since funds were deducted during initial pending request
    - Logs rejection with reason
    """
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.status != 'Pending':
        log_security_event('INVALID_TRANSACTION_REJECTION', user_id=current_user.id, username=current_user.username, 
                         details=f'Transaction {transaction_id} already processed', severity='WARNING')
        flash('Transaction is already processed.', 'warning')
        return redirect(url_for('admin.pending_transactions'))
    
    user = User.query.get(transaction.user_id)
    
    # Refund balance since funds were deducted during the initial pending request
    if transaction.type == 'withdrawal':
        user.balance += transaction.amount
        
    transaction.status = 'Rejected'
    transaction.rejection_reason = 'Rejected by administrator'
    transaction.approved_by = current_user.id
    transaction.approved_at = datetime.utcnow()
    db.session.commit()
    
    log_security_event('TRANSACTION_REJECTED', user_id=current_user.id, username=current_user.username, 
                     details=f'Transaction {transaction_id}: {transaction.type} of ${transaction.amount:.2f} for {user.username}')
    flash(f'Transaction rejected for {user.username}. Funds refunded if applicable.', 'info')
    return redirect(url_for('admin.pending_transactions'))


@admin.route("/settings", methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """
    Handles global administrative settings updates with validation.
    
    - Validates withdrawal limit is a valid amount
    - Logs all setting changes for audit trail
    """
    if request.method == 'POST':
        limit_str = request.form.get('withdrawal_limit', '').strip()
        
        # Validate withdrawal limit
        is_valid, amount_or_error = validate_amount(limit_str)
        if not is_valid:
            log_security_event('INVALID_SETTINGS_UPDATE', user_id=current_user.id, username=current_user.username, 
                             details=f'Invalid withdrawal limit: {limit_str}', severity='WARNING')
            flash('Invalid withdrawal limit. ' + amount_or_error, 'danger')
            config = SystemConfig.query.filter_by(key='withdrawal_limit').first()
            limit = config.value if config else "1000"
            return render_template('admin/settings.html', title='System Settings', withdrawal_limit=limit)
        
        amount = amount_or_error
        config = SystemConfig.query.filter_by(key='withdrawal_limit').first()
        old_value = config.value if config else None
        
        if not config:
            config = SystemConfig(
                key='withdrawal_limit', 
                value=str(amount), 
                description='Max withdrawal amount before admin approval'
            )
            db.session.add(config)
        else:
            config.value = str(amount)
            config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_security_event('SETTINGS_UPDATED', user_id=current_user.id, username=current_user.username, 
                         details=f'withdrawal_limit changed from {old_value} to {amount}')
        flash('System settings updated.', 'success')
        return redirect(url_for('admin.settings'))
        
    config = SystemConfig.query.filter_by(key='withdrawal_limit').first()
    limit = config.value if config else "1000"
    return render_template('admin/settings.html', title='System Settings', withdrawal_limit=limit)


# --- API ENDPOINTS FOR AJAX ---

@admin.route("/api/user/<int:user_id>/toggle-status", methods=['POST'])
@login_required
@admin_required
def api_toggle_user_status(user_id):
    """
    AJAX JSON endpoint to freeze or activate a customer account.
    
    - Returns JSON response for AJAX calls
    - Prevents self-suspension
    - Logs account status changes
    """
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        log_security_event('SELF_SUSPENSION_ATTEMPT', user_id=current_user.id, username=current_user.username, severity='WARNING')
        return jsonify({"success": False, "message": "You cannot freeze your own account!"}), 400
    
    old_status = user.status
    user.status = 'Suspended' if user.status == 'Active' else 'Active'
    db.session.commit()
    
    log_security_event('USER_STATUS_CHANGED_VIA_API', user_id=current_user.id, username=current_user.username, 
                     details=f'Changed user {user.username} from {old_status} to {user.status}')
    
    return jsonify({
        "success": True, 
        "message": f"Account {user.status} successfully.",
        "new_status": user.status
    })


@admin.route("/api/transaction/<int:transaction_id>/approve", methods=['POST'])
@login_required
@admin_required
def api_approve_transaction(transaction_id):
    """
    AJAX JSON endpoint to finalize and approve a pending transaction.
    
    - Returns JSON response for AJAX calls
    - Validates transaction is still pending
    - Updates status and logs approval
    """
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.status != 'Pending':
        log_security_event('INVALID_TRANSACTION_APPROVAL_VIA_API', user_id=current_user.id, username=current_user.username, 
                         details=f'Transaction {transaction_id} already processed', severity='WARNING')
        return jsonify({"success": False, "message": "Transaction already processed."}), 400
    
    transaction.status = 'Completed'
    transaction.approved_by = current_user.id
    transaction.approved_at = datetime.utcnow()
    db.session.commit()
    
    log_security_event('TRANSACTION_APPROVED_VIA_API', user_id=current_user.id, username=current_user.username, 
                     details=f'Transaction {transaction_id} approved')
    
    return jsonify({"success": True, "message": "Transaction confirmed."})


@admin.route("/api/transaction/<int:transaction_id>/reject", methods=['POST'])
@login_required
@admin_required
def api_reject_transaction(transaction_id):
    """AJAX JSON endpoint to cancel a pending transaction with rejection details."""
    data = request.get_json() or {}
    reason = data.get('reason', 'No reason provided')
    
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.status != 'Pending':
        return {"success": False, "message": "Transaction already processed."}, 400
    
    user = User.query.get(transaction.user_id)
    if transaction.type == 'withdrawal':
        user.balance += transaction.amount
        
    transaction.status = 'Rejected'
    transaction.rejection_reason = reason
    db.session.commit()
    return {"success": True, "message": f"Transaction cancelled: {reason}"}


@admin.route("/api/stats")
@login_required
@admin_required
def api_stats():
    """AJAX JSON endpoint yielding historical transaction volumes for chart widgets."""
    days = []
    counts = []
    for i in range(6, -1, -1):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        count = Transaction.query.filter(db.func.date(Transaction.timestamp) == date).count()
        days.append(date.strftime('%b %d'))
        counts.append(count)
    
    return {"labels": days, "data": counts}


@admin.route("/inbox")
@login_required
@admin_required
def inbox():
    """Renders support inbox aggregating general customer support tickets."""
    messages = SupportMessage.query.filter_by(recipient_id=None).order_by(SupportMessage.timestamp.desc()).all()
    return render_template('admin/inbox.html', title='Admin Inbox', messages=messages)


@admin.route("/message/<int:message_id>/reply", methods=['POST'])
@login_required
@admin_required
def reply_message(message_id):
    """HTML redirection handler to submit correspondence replies to user support tickets."""
    original_msg = SupportMessage.query.get_or_404(message_id)
    reply_body = request.form.get('reply')
    
    if reply_body:
        reply = SupportMessage(
            subject=f"Re: {original_msg.subject}",
            message=reply_body,
            sender=current_user,
            recipient_id=original_msg.sender_id
        )
        original_msg.is_read = True
        db.session.add(reply)
        db.session.commit()
        flash('Reply sent successfully.', 'success')
    
    return redirect(url_for('admin.inbox'))
