# CodexActivityApp

A FastAPI business portal with login/registration by organisation, MySQL persistence, and marker panel submissions.

## Features
- Login with **email + password + organisation**.
- Create account flow with organisation selection or creation.
- Marker panel submission workflow with:
  - file upload + required-column validation (order independent)
  - contact details form
  - successful persistence + dashboard confirmation message
- MySQL-backed entities:
  - `organisations(id, name)`
  - `users(id, email, hashed_pw, organisation_id)`
  - `submissions(id, user_id, organisation_id, file_blob, original_filename, date_submitted, ...contact fields...)`
- PBKDF2 password hashing using Python standard library (`hashlib.pbkdf2_hmac`).
- Authenticated home page shows organisation and member list.
- Logout support.

## Prerequisites
- Python 3.10+
- MySQL 8+

## 1) Create database and SQL user
Run this in MySQL as an admin user:

```sql
CREATE DATABASE codex_activity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_app_pw';
CREATE USER 'codex_app'@'127.0.0.1' IDENTIFIED BY 'codex_app_pw';

GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'localhost';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

## 2) Configure environment
Set these environment variables (or rely on defaults for local dev):

```bash
export DATABASE_URL='mysql+pymysql://codex_app:codex_app_pw@127.0.0.1:3306/codex_activity'
export SESSION_SECRET='replace-with-a-random-secret'
# Optional:
export PBKDF2_ITERATIONS=260000
```

## 3) Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Using `run_app.sh`
`run_app.sh` will:
1. Pull latest changes.
2. Create/update `.venv`.
3. Install dependencies.
4. **Wipe and recreate database tables**.
5. Launch Uvicorn.

> Ensure `DATABASE_URL` points at the desired DB before running `run_app.sh`, because it resets all app tables.
