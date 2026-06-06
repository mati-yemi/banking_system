# 🚀 Deploying NeoBank to PythonAnywhere

## Prerequisites

✅ GitHub account  
✅ PythonAnywhere account (free or paid)  
✅ Git installed locally  
✅ Your banking system code ready

---

## Step 1: Prepare Your Code for PythonAnywhere

### 1.1 Create `.gitignore` file

Create a `.gitignore` file in your project root:

```
# Virtual environments
venv/
env/
ENV/

# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so

# Flask instance folder
instance/

# Database files (don't commit local DBs)
*.db
*.sqlite
*.sqlite3

# Environment variables
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Test coverage
.coverage
htmlcov/

# Build artifacts
build/
dist/
*.egg-info/
```

### 1.2 Create `.env.example`

Create `.env.example` to document required environment variables:

```
# Flask Configuration
FLASK_ENV=production
FLASK_APP=run.py

# Security
SECRET_KEY=your-secret-key-here-change-in-production
REMEMBER_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
WTF_CSRF_SSL_STRICT=True

# Database (PythonAnywhere uses MySQL by default)
DATABASE_URL=mysql://username:password@username.mysql.pythonanywhere.com/username$databasename

# Port
PORT=80

# Audit logging
AUDIT_LOG_FILE=/var/log/neobank/audit.log
```

### 1.3 Initialize Git Repository

```bash
cd path/to/banking_system
git init
git add .
git config user.email "your-email@example.com"
git config user.name "Your Name"
git commit -m "Initial commit - NeoBank banking system"
git branch -M main
```

### 1.4 Push to GitHub

1. Create a **new repository** on GitHub (don't initialize with README)
2. Push your code:

```bash
git remote add origin https://github.com/your-username/neobank.git
git push -u origin main
```

---

## Step 2: Set Up PythonAnywhere

### 2.1 Sign Up & Login

1. Go to [www.pythonanywhere.com](https://www.pythonanywhere.com)
2. Create a free account (or use paid if you want better resources)
3. Login to your dashboard

### 2.2 Create a Web App

1. In Dashboard → **Web** → **Add a new web app**
2. Choose **Manual configuration** (not framework pre-sets)
3. Select **Python 3.11** (or latest 3.x available)
4. Note your web app configuration URL

---

## Step 3: Configure Your Web App

### 3.1 Clone Your Repository

Go to **Consoles** → **Bash console**

```bash
cd /home/your_username
git clone https://github.com/your-username/neobank.git
cd neobank/banking_system
```

### 3.2 Create Virtual Environment

**Important:** The virtual environment should be created in the `banking_system` directory.

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Set Environment Variables

Go to **Web** → **your_web_app_name** → **Web app settings**

Scroll to **Virtualenv section** and set the path to:
```
/home/your_username/neobank/banking_system/venv
```

Scroll to **Environment variables** section and add:

```
FLASK_APP=/home/your_username/neobank/banking_system/run.py
FLASK_ENV=production
SECRET_KEY=generate-a-secure-key-here-use-python-secrets
DATABASE_URL=mysql://your_username:password@your_username.mysql.pythonanywhere.com/your_username$neobank
SESSION_COOKIE_SECURE=True
REMEMBER_COOKIE_SECURE=True
WTF_CSRF_SSL_STRICT=True
```

**To generate a secure SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3.4 Create WSGI Configuration File

Go to **Web** → **your_web_app_name** → **Code** section

Click the **WSGI configuration file** link. It opens at:
```
/var/www/your_username_pythonanywhere_com_wsgi.py
```

**Replace the entire content with:**

```python
"""
WSGI Configuration for NeoBank on PythonAnywhere
"""
import sys
import os

# Add your project directory to the Python path
project_home = '/home/your_username/neobank/banking_system'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtual environment
activate_this = os.path.join(project_home, 'venv', 'bin', 'activate_this.py')
exec(open(activate_this).read(), {'__file__': activate_this})

# Set working directory
os.chdir(project_home)

# Import and run the Flask app
from app import create_app

app = create_app()

# Use the Flask app as the WSGI application
application = app
```

**Click Save** ✅

### 3.5 Configure Static Files

Go to **Web** → **your_web_app_name** → **Static files** section

Add these entries:
banking_system/
| URL | Directory |
|-----|-----------|
| `/static/` | `/home/your_username/neobank/app/static` |

---

## Step 4: Initialize Database

### 4.1 Create Database on PythonAnywhere

1. Go to **Databases** tab
2. Click **Create a new database**
3. Choose **MySQL**
4. Set password (copy this for DATABASE_URL)
5. Wait for initialization (2-3 minutes)

Note your database details:
- **Username**: `your_username`
- **Database**: `your_username$neobank`
- **Host**: `your_username.mysql.pythonanywhere.com`

### 4.2 Create Tables

Go to **Consoles** → **Bash co/banking_systemnsole**

```bash
cd /home/your_username/neobank
source venv/bin/activate

# Create tables and run migrations
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('✓ Database tables created successfully')
"
```

### 4.3 Seed Admin User (Optional)

```bash
python seed_admin.py
```

Follow the prompts to create an admin account.

---

## Step 5: Enable HTTPS & Deploy

### 5.1 Enable HTTPS

1. Go to **Web** → **your_web_app_name**
2. Scroll to **HTTPS section**
3. Click **Add a FREE certificate** (Let's Encrypt)
4. PythonAnywhere will automatically set it up

### 5.2 Reload Web App

1. Click the **Reload web app** button (green button at top)
2. Wait 30 seconds for changes to take effect

### 5.3 Access Your App

Your app is now live at:
```
https://your_username.pythonanywhere.com
```

---

## Step 6: Post-Deployment Checklist

- [ ] Access your web app URL in browser
- [ ] Test login with your admin credentials
- [ ] Verify database connectivity
- [ ] Test deposit/withdrawal features
- [ ] Check that static files load (CSS, JS)
- [ ] Verify HTTPS is working (lock icon in browser)
- [ ] Check logs for errors (see below)

---

## Troubleshooting

### View Error Logs

Go to **Web** → **your_web_app_name** → **Log files** section

Key logs:
- **Error log** - Application errors
- **Access log** - HTTP requests
- **Server log** - Server status

**View logs in Bash console:**
```bash
tail -f /var/log/your_username.pythonanywhere.com.error.log
```

### Common Issues

#### ❌ 500 Internal Server Error

Check error logs for:
1. **Import errors** - Missing packages in requirements.txt
2. **Database connection** - Wrong DATABASE_URL or credentials
3. **Missing environment variables** - Check Web app settings

**Fix:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

#### ❌ Static Files Not Loading (404)

Ensure static files path is correct in Web settings:
```
/home/your_username/neobank/app/static
```

Then reload web app.

#### ❌ Database Connection Failed

Test the connection in Bash:
```bash
mysql -h your_username.mysql.pythonanywhere.com -u your_username -p
```

Enter password and verify you can connect.

#### ❌ Template Rendering Issues

Ensure templates path in `app/__init__.py` is correct:
```python
app = Flask(__name__, template_folder='templates')
```

---

## Updating Your App

### 1. Push Changes to GitHub

```bash
cd /path/to/yemi  # Navigate to the root directory
git add .
git commit -m "Description of changes"
git push origin main
```

### 2. Pull Changes on PythonAnywhere

Go to **Consoles** → **Bash console**

```bash
cd /home/your_username/neobank  # Root directory
git pull origin main

# If you have new dependencies
cd /home/your_username/neobank/banking_system
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Reload Web App

In Web app settings, click **Reload web app**

---

## Production Security Checklist

- ✅ **SECRET_KEY** - Set to a strong random value
- ✅ **DATABASE_URL** - Using secure credentials
- ✅ **HTTPS** - Enabled with Let's Encrypt
- ✅ **CSRF Protection** - Enabled in config
- ✅ **SQL Injection** - Using SQLAlchemy ORM
- ✅ **Rate Limiting** - Configured for login attempts
- ✅ **Password Requirements** - 12+ chars, uppercase, digits, special
- ✅ **Audit Logging** - Enabled for sensitive operations

---

## Performance Tips

1. **Enable Caching** - Add Redis caching for sessions
2. **Optimize Database** - Add indexes for frequently queried columns
3. **Compress Static Files** - Enable GZIP compression
4. **Use Paid Plan** - Free tier has limitations (100MB disk, 1 CPU core)

---

## Getting Help

- **PythonAnywhere Help** - https://www.pythonanywhere.com/help/
- **PythonAnywhere Forums** - https://www.pythonanywhere.com/forums/
- **Flask Documentation** - https://flask.palletsprojects.com/
- **Your Error Logs** - Always check them first!

---

**Your app is now live! 🎉**

Visit: `https://your_username.pythonanywhere.com`

