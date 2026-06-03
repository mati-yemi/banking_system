# 🏦 NeoBank - Premium Digital Banking System

NeoBank is a state-of-the-art, secure, and visually stunning digital banking application built with **Flask**, **SQLAlchemy**, and designed with a premium, responsive dark-mode glassmorphism interface.

---

## 🌟 Key Features

### 👤 User Capabilities
- **Fluid Authentication**: Secure registration and login using encrypted passwords powered by `Flask-Bcrypt`.
- **Deposit & Instant Withdrawal**: Instantly deposit funds or withdraw with strict balance validation.
- **Administrative Withdrawal Limits**: Safe banking mechanics that automatically mark withdrawals exceeding system limits as *Pending Admin Approval*.
- **Inter-User Transfers**: Transfer funds safely to other registered NeoBank users with real-time email existence verification using AJAX.
- **Support Ticketing System**: Contact support directly with custom support requests and read response tickets instantly in a conversational format.

### 🛡️ Administrative Capabilities
- **Unified Control Panel**: Real-time summary dashboard of total system users, total system balance, and active queue of pending transactions.
- **User Management**: Freeze/suspend or activate accounts on the fly to protect system integrity.
- **Pending Approvals Manager**: Review, approve, or reject pending large withdrawals with customizable rejection reasons.
- **System Parameter Tuning**: Update system variables such as the global withdrawal approval threshold instantly.
- **Support Inbox & Correspondence**: Threaded support inbox enabling administrators to respond to individual customer tickets seamlessly.

---

## 📂 Codebase Architecture

The project is structured following the **Flask Blueprint** design pattern, ensuring modularity, isolation of concerns, and scalability:

```text
banking_system/
├── app/
│   ├── admin/                # Administrative blueprints & routes
│   │   └── routes.py
│   ├── auth/                 # Authentication blueprints, forms, and routes
│   │   ├── forms.py
│   │   └── routes.py
│   ├── banking/              # Banking ledger, transfer, support ticket routes
│   │   └── routes.py
│   ├── static/               # Assets, styles, and javascript functions
│   │   ├── js/
│   │   │   └── main.js
│   │   └── style.css
│   ├── templates/            # HTML views categorized by blueprint
│   │   ├── admin/
│   │   └── *.html
│   ├── __init__.py           # Application factory, extensions initialization, context processors
│   ├── extensions.py         # App extension definitions (DB, Login, Bcrypt, CSRF)
│   └── models.py             # SQLAlchemy Database Schema models
├── instance/                 # Local dynamic data storage folder
├── .env                      # Local environment configurations (private)
├── .gitignore                # Repository file ignore settings
├── config.py                 # Application configuration setups
├── requirements.txt          # Python dependency packages
├── run.py                    # Main app entry point script
├── seed_admin.py             # Administrative seeder script
└── test_db.py                # Database connection check script
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Configure Environment
Create a `.env` file in the root of the project (`banking_system/.env`) with the following environment variables:
```env
SECRET_KEY=super-secret-key-change-in-production
FLASK_APP=run.py
FLASK_DEBUG=1
DATABASE_URL=sqlite:///app.db
```

### 3. Install Dependencies
Install all package requirements using `pip`:
```bash
pip install -r requirements.txt
```

### 4. Initialize & Seed Administrative Account
To initialize the database schemas and generate the predefined administrative user:
```bash
python seed_admin.py
```
This initializes the database schema, configures default parameters, and seeds the default admin user:
- **Username**: `MATI YEMI ANGELE`
- **Email**: `matiyem71@gamil.com`
- **Password**: `Angel1234`
- **Initial Balance**: `$1,000,000.00`

### 5. Run the Application
Start the Flask development server:
```bash
python run.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser to access NeoBank.

---

## 🛡️ Security Best Practices
NeoBank is built with standard defense measures to protect financial records:
- **CSRF Protection**: All routes and form submittals are protected by `Flask-WTF` CSRF tokens, preventing Cross-Site Request Forgery.
- **Secure Hashing**: User passwords are saved as secure cryptographic hashes using `PBKDF2 with SHA-256`.
- **Session Authentication**: Secure cookie-based login state protection using `Flask-Login`.
- **Access Guarding**: Role-based access validation decorators (`@admin_required` and `@active_account_required`) preventing arbitrary access to customer ledgers or administrative routes.
