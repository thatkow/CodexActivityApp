# CodexActivityApp

Basic business-style FastAPI app with:
- Login by **organisation + email + password**
- Create account flow with an option to **create a new organisation**
- MySQL-backed persistence for organisations and users
- Organisation dashboard with members list and logout

## Tech stack
- FastAPI + Uvicorn
- SQLAlchemy ORM
- MySQL + PyMySQL driver
- Password hashing using Python standard library `hashlib.pbkdf2_hmac`

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

Optional (defaults are already set in `main.py`). You can configure either with exported vars or a local `.env` file (auto-loaded on startup):

```bash
export DATABASE_URL='mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app'
export APP_SECRET_KEY='replace-with-a-long-random-secret'
export PANEL_ADMIN='admin'
export PANEL_ADMIN_PW='password'
export APP_BASE_URL='http://127.0.0.1:8000'

# SMTP settings for submission notifications
export SMTP_HOST='smtp.example.com'
export SMTP_PORT='587'
export SMTP_USER='smtp-user'
export SMTP_PASSWORD='smtp-password'
export SMTP_FROM='no-reply@example.com'
export SMTP_USE_TLS='true'
export EMAIL_VERBOSE='true'
```

Example `.env`:

```env
DATABASE_URL=mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app
APP_SECRET_KEY=replace-with-a-long-random-secret
PANEL_ADMIN=admin
PANEL_ADMIN_PW=password
APP_BASE_URL=http://127.0.0.1:8000
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=smtp-user
SMTP_PASSWORD=smtp-password
SMTP_FROM=no-reply@example.com
SMTP_USE_TLS=true
EMAIL_VERBOSE=true
```


## Admin panel + subscribers
- Open `/admin` and log in with `PANEL_ADMIN` / `PANEL_ADMIN_PW`.
- Use the **Subscribers** button in the admin page to manage notification recipients.
- When a marker panel is submitted, the app sends an email to all subscribers with a direct link to that submission in the admin view.
- If your SMTP relay on port 25 does not use STARTTLS, set `SMTP_USE_TLS=false`.

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
