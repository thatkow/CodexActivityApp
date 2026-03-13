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

Optional (defaults are already set in `main.py`):

```bash
export DATABASE_URL='mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app'
export APP_SECRET_KEY='replace-with-a-long-random-secret'
```

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
