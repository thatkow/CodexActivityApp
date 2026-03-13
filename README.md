# CodexActivityApp

Basic business-style FastAPI app with:
- Login by **organisation + email + password**
- Create account flow with an option to **create a new organisation**
- MySQL-backed persistence for organisations and users
- Organisation dashboard with members list and logout
- Marker panel submissions with admin review
- Admin subscriber list for email notifications on new submissions

## Tech stack
- FastAPI + Uvicorn
- SQLAlchemy ORM
- MySQL + PyMySQL driver
- Password hashing using Python standard library `hashlib.pbkdf2_hmac`
- SMTP email notifications using Python standard library `smtplib`

## 1) Create MySQL database + app user

Log into MySQL as an admin user and run:

```sql
CREATE DATABASE codex_activity_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_app_password';
CREATE USER 'codex_app'@'127.0.0.1' IDENTIFIED BY 'codex_app_password';

GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'localhost';
GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

## 2) Configure app environment variables

Create a `.env` file in the project root (or export variables in your shell):

```bash
DATABASE_URL='mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app'
APP_SECRET_KEY='replace-with-a-long-random-secret'

# Admin login
PANEL_ADMIN='admin'
PANEL_ADMIN_PW='password'

# Used in subscriber email links to admin submission detail page
APP_BASE_URL='http://127.0.0.1:8000'

# SMTP settings (required to send subscriber notifications)
SMTP_HOST='smtp.example.com'
SMTP_PORT='587'
SMTP_USERNAME='smtp-user'
SMTP_PASSWORD='smtp-password'
SMTP_USE_TLS='true'
SMTP_SENDER='noreply@example.com'
```

If `SMTP_HOST` or `SMTP_SENDER` is blank, notification emails are skipped.

## 3) Run app

```bash
chmod +x run_app.sh
./run_app.sh
```

The app runs at `http://127.0.0.1:8000`.

## Notes about `run_app.sh`
`run_app.sh` now does the following before launch:
1. Pulls latest changes
2. Creates/activates virtual environment
3. Installs dependencies
4. **Drops and recreates all database tables**
5. Starts Uvicorn

This is intended for quick reset/demo workflows.
