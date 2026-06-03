# NeoBank Security Implementation Guide

## Overview
This document outlines the comprehensive security improvements implemented in the NeoBank banking system to prevent unauthorized access, data breaches, and common web vulnerabilities.

---

## 1. Authentication & Authorization Security

### 1.1 Strong Password Requirements
**File**: `app/auth/forms.py`, `app/security.py`

**Implementation**:
- Minimum 12 characters (configurable via `PASSWORD_MIN_LENGTH`)
- Requires uppercase letters (A-Z)
- Requires lowercase letters (a-z)
- Requires digits (0-9)
- Requires special characters (!@#$%^&*...)

**Function**: `validate_password_strength()` in `app/security.py`

```python
# Example of valid password:
# MyBank@2024Secure
```

### 1.2 Account Lockout Protection
**File**: `app/auth/routes.py`

**Features**:
- Maximum 5 failed login attempts per 15 minutes
- Automatic account lockout after 5 failed attempts
- Failed attempt counter resets on successful login
- Admin can manually unlock accounts via database

**Protection Against**: Brute force attacks

### 1.3 Secure Password Hashing
**File**: `app/auth/routes.py`, `app/extensions.py`

**Implementation**:
- Uses bcrypt with automatic salt generation
- Passwords are hashed with high computational cost
- Legacy password hashes automatically upgraded to bcrypt on login
- Password never stored in plaintext

**Technology**: Flask-Bcrypt (bcrypt library)

### 1.4 Session Security
**File**: `config.py`

**Configuration**:
```python
# Session cookies are HTTP-only (not accessible via JavaScript)
SESSION_COOKIE_HTTPONLY = True

# Secure flag set for HTTPS (production)
SESSION_COOKIE_SECURE = True

# SameSite protection against CSRF
SESSION_COOKIE_SAMESITE = 'Lax'

# Session timeout: 2 hours
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

# Refresh session on each request
SESSION_REFRESH_EACH_REQUEST = True
```

---

## 2. Input Validation & Sanitization

### 2.1 Amount Validation
**File**: `app/security.py`

**Function**: `validate_amount()`

**Validations**:
- Amount must be greater than zero
- Maximum transaction limit: $1,000,000,000
- Maximum 2 decimal places
- Prevents negative amounts
- Prevents extremely large amounts

**Usage**: All deposit, withdrawal, and transfer operations

### 2.2 Input Sanitization
**File**: `app/security.py`

**Function**: `sanitize_input()`

**Protections**:
- Removes all HTML tags
- Prevents XSS (Cross-Site Scripting) attacks
- Strips dangerous content
- Limits input length (default 255 characters)

**Applied To**:
- All user inputs (username, email, messages)
- Form submissions
- API parameters

### 2.3 Email Validation
**File**: `app/auth/forms.py`

**Features**:
- Valid email format required
- Domain validation
- Prevents email header injection

---

## 3. Database Security

### 3.1 Environment Variables (Secrets Management)
**File**: `config.py`, `.env.example`

**Never commit sensitive data to version control**:

```bash
# .env file (NEVER commit to git)
SECRET_KEY=your-super-secret-key-minimum-32-characters
DATABASE_URL=postgresql://user:password@localhost:5432/neobank
```

**In code**:
```python
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///neobank.db')
```

**Protection**: Credentials are not exposed in source code

### 3.2 SQL Injection Prevention
**File**: `app/models.py`, all route files

**Implementation**:
- Uses SQLAlchemy ORM (parameterized queries)
- No raw SQL queries
- Automatic query parameter escaping
- Type checking for all database columns

### 3.3 Database Connection Security
**File**: `config.py`

**Configuration**:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,  # Connection health check
}
```

---

## 4. Cross-Site Request Forgery (CSRF) Protection

**File**: `app/extensions.py`, `config.py`

**Implementation**:
- CSRF tokens on all forms
- SameSite cookies
- Automatic token validation
- Token bound to session

**How it works**:
1. Server generates unique CSRF token
2. Token included in all forms as hidden field
3. Token validated on form submission
4. Invalid or missing tokens rejected

---

## 5. Rate Limiting & DoS Protection

**File**: `app/extensions.py`, route files

**Implementation**:
- Prevents brute force attacks
- Protects against DoS (Denial of Service)

**Rate Limits**:
```python
# Login: 10 per hour
@auth.route("/login", methods=['GET', 'POST'])
@limiter.limit("10 per hour")

# Registration: 5 per hour
@auth.route("/register", methods=['GET', 'POST'])
@limiter.limit("5 per hour")

# Deposits: 20 per hour
@banking.route("/deposit", methods=['GET', 'POST'])
@limiter.limit("20 per hour")

# Support: 10 per hour
@banking.route("/support", methods=['GET', 'POST'])
@limiter.limit("10 per hour")
```

---

## 6. Security Headers

**File**: `config.py`, `app/__init__.py`

**Applied to all responses**:

```python
SECURITY_HEADERS = {
    # Enforce HTTPS
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    
    # Prevent MIME type sniffing
    'X-Content-Type-Options': 'nosniff',
    
    # Clickjacking protection
    'X-Frame-Options': 'DENY',
    
    # XSS protection
    'X-XSS-Protection': '1; mode=block',
    
    # Content Security Policy
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';",
    
    # Referrer Policy
    'Referrer-Policy': 'strict-origin-when-cross-origin',
}
```

---

## 7. Audit Logging

**File**: `app/security.py`, all route files

**Features**:
- Logs all security-relevant events
- Includes timestamp, user info, IP address
- Event severity levels (INFO, WARNING, CRITICAL)
- File-based logging to `logs/audit.log`

**Logged Events**:
- Login success/failure
- Failed login attempts (brute force)
- Account lockouts
- Unauthorized access attempts
- Transaction operations
- Admin actions
- Settings changes

**Example**:
```python
log_security_event(
    'TRANSACTION_SUCCESS', 
    user_id=current_user.id,
    username=current_user.username,
    details=f'Transfer to {recipient.username}: ${amount:.2f}'
)
```

**Log Format**:
```
[2024-01-15 14:30:45] INFO - LOGIN_SUCCESS | User: john_doe (ID: 5) | IP: 192.168.1.1
[2024-01-15 14:31:12] WARNING - BRUTE_FORCE_ATTEMPT | Too many login attempts from 192.168.1.2
[2024-01-15 14:32:00] CRITICAL - UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT | Attempted access to /admin/dashboard
```

---

## 8. Account Management Security

### 8.1 Account Number Generation
**File**: `app/models.py`

**Function**: `generate_account_number()`

**Improvement**: Changed from `random.choices()` to `secrets.choice()`
- Uses cryptographically secure randomness
- Prevents predictable account numbers
- Each number is unique

### 8.2 User Status Tracking
**File**: `app/models.py`

**New Fields**:
```python
failed_login_attempts = db.Column(db.Integer, default=0)
locked_until = db.Column(db.DateTime, nullable=True)
password_changed_at = db.Column(db.DateTime, nullable=True)
created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
last_login = db.Column(db.DateTime, nullable=True)
```

---

## 9. Transaction Security

### 9.1 Double-Entry Bookkeeping
**File**: `app/banking/routes.py`

**Protection**: Every transfer creates two ledger entries
```python
# Sender: transfer_out
# Recipient: transfer_in
```

This ensures accounting integrity and audit trail.

### 9.2 Approval Workflow
**File**: `app/banking/routes.py`, `app/admin/routes.py`

**Large Withdrawal Process**:
1. User initiates withdrawal > limit
2. Balance deducted immediately (prevents double-spending)
3. Transaction marked as "Pending"
4. Admin reviews and approves/rejects
5. Balance refunded if rejected

---

## 10. Error Handling & Information Disclosure

### 10.1 Generic Error Messages
**Purpose**: Prevent information leakage to attackers

**Example - Login**:
```python
# Bad: "User not found" or "Invalid password"
# Good: "Login Unsuccessful. Please check email and password."
```

This prevents username enumeration attacks.

### 10.2 Error Handlers
**File**: `app/__init__.py`

```python
@app.errorhandler(403)
def forbidden(error):
    return {'error': 'Access Forbidden'}, 403

@app.errorhandler(404)
def not_found(error):
    return {'error': 'Page Not Found'}, 404

@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return {'error': 'Internal Server Error'}, 500
```

---

## 11. Environment Configuration

### 11.1 Configuration Classes
**File**: `config.py`

**Three Configurations**:

1. **DevelopmentConfig**
   - Debug enabled
   - CSRF disabled for testing
   - Relaxed security headers

2. **ProductionConfig** (STRICT)
   - Debug disabled
   - HTTPS enforced
   - CSRF enabled
   - Secure cookies
   - Requires SECRET_KEY environment variable

3. **TestingConfig**
   - In-memory SQLite database
   - CSRF disabled
   - Relaxed rate limiting

**Activation**:
```bash
# Development
export FLASK_ENV=development

# Production
export FLASK_ENV=production
export SECRET_KEY=<very-long-random-key>
export DATABASE_URL=postgresql://...
```

---

## 12. Deployment Security Checklist

### Essential for Production:
- [ ] Set `FLASK_ENV=production`
- [ ] Generate strong `SECRET_KEY` (minimum 32 characters)
- [ ] Use PostgreSQL with strong credentials
- [ ] Enable HTTPS/SSL certificate
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Set `WTF_CSRF_SSL_STRICT=True`
- [ ] Configure firewall to allow only necessary ports
- [ ] Enable audit logging
- [ ] Regular database backups
- [ ] Monitor audit logs for suspicious activity
- [ ] Keep dependencies updated
- [ ] Run security scanner (e.g., OWASP ZAP)
- [ ] Implement Web Application Firewall (WAF)

---

## 13. Vulnerability Mitigation

### 13.1 Common Attacks Prevented

| Attack Type | Prevention Method |
|---|---|
| SQL Injection | SQLAlchemy ORM, parameterized queries |
| XSS (Cross-Site Scripting) | Input sanitization, template escaping |
| CSRF (Cross-Site Request Forgery) | CSRF tokens, SameSite cookies |
| Brute Force | Account lockout, rate limiting |
| DoS (Denial of Service) | Rate limiting, connection pooling |
| Session Hijacking | Secure cookies, HTTPS enforcement |
| Information Disclosure | Generic error messages, header removal |
| Timing Attacks | Constant-time password comparison |

---

## 14. Dependencies & Security

**File**: `requirements.txt`

**Key Security Libraries**:
- `Flask-Bcrypt`: Password hashing
- `Flask-WTF`: CSRF protection
- `Flask-Login`: Session management
- `Flask-Limiter`: Rate limiting
- `bleach`: XSS prevention
- `werkzeug>=3.0.0`: Secure utilities
- `cryptography`: Encryption support

**Maintenance**:
```bash
# Check for vulnerable packages
pip install safety
safety check

# Update all packages regularly
pip install --upgrade --upgrade-strategy eager -r requirements.txt
```

---

## 15. Monitoring & Incident Response

### 15.1 Audit Log Monitoring
**Location**: `logs/audit.log`

**Key Metrics to Monitor**:
- Failed login attempts
- Brute force attempts
- Unauthorized access attempts
- Unusual transaction patterns
- Settings changes

### 15.2 Alerting Setup
Monitor for:
- Multiple failed login attempts from same IP
- Multiple unauthorized access attempts
- Unusually large transactions
- Settings changes
- Admin account modifications

---

## 16. Testing Security

**Recommended Tools**:
- OWASP ZAP: Web application scanning
- Burp Suite: Penetration testing
- SQLmap: SQL injection detection
- Hydra: Password cracking (for authorized testing)

---

## 17. Future Security Enhancements

1. **Two-Factor Authentication (2FA)**
   - TOTP (Time-based One-Time Password)
   - SMS-based verification

2. **API Keys for External Access**
   - Rate limiting per API key
   - Scope-based permissions

3. **Encryption at Rest**
   - Encrypt sensitive data in database
   - HSM (Hardware Security Module) for key storage

4. **IP Whitelisting**
   - Allow access only from known locations
   - Configurable per user

5. **Machine Learning**
   - Anomaly detection for transactions
   - Fraud prevention

6. **Hardware Tokens**
   - Physical security keys
   - U2F/FIDO2 support

---

## 18. Compliance

This system implements controls for:
- **PCI DSS** (Payment Card Industry Data Security Standard)
- **OWASP Top 10** (Web application security)
- **GDPR** (Data protection - basic implementation)
- **SOC 2** (Security controls)

---

## 19. Quick Reference

### Start Development Server:
```bash
# Set environment variables
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key

# Install dependencies
pip install -r requirements.txt

# Run server
python run.py
```

### View Audit Logs:
```bash
tail -f logs/audit.log
```

### Generate Strong Secret Key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 20. Support & Updates

- Review security updates regularly
- Subscribe to Flask security announcements
- Monitor OWASP for new vulnerabilities
- Conduct annual security audits
- Perform penetration testing

---

**Last Updated**: January 2024
**Security Level**: Bank-Grade (Implementation Phase)
