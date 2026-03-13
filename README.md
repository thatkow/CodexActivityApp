# CodexActivityApp

A small FastAPI business-style portal with:
- Organisation-aware login (`email + password + organisation`)
- Account creation with existing org selection or creating a new org
- MySQL-backed storage
- Organisation dashboard with member list and logout

## Database model

- `organisations`
  - `id` (PK)
  - `name` (unique)
- `users`
  - `id` (PK)
  - `email` (unique)
  - `hashed_pw`
  - `organisation_id` (FK -> `organisations.id`)

Passwords use the Python standard-library PBKDF2 implementation (`hashlib.pbkdf2_hmac`).

## Prerequisites

- Python 3.10+
- MySQL 8+
- `mysql` CLI available in your shell

## Environment variables

The app and `run_app.sh` both use these values (with defaults):

- `MYSQL_HOST` (default: `127.0.0.1`)
- `MYSQL_PORT` (default: `3306`)
- `MYSQL_DATABASE` (default: `codex_activity_app`)
- `MYSQL_USER` (default: `codex_app`)
- `MYSQL_PASSWORD` (default: `codex_app_password`)
- `MYSQL_ROOT_USER` (default: `root`) — used by `run_app.sh` only
- `MYSQL_ROOT_PASSWORD` (default: empty) — used by `run_app.sh` only
- `SESSION_SECRET` (default: `change-me-in-production`)

## Database setup (manual)

If you prefer to provision manually, create an app user and database:

```sql
CREATE DATABASE codex_activity_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codex_app'@'%' IDENTIFIED BY 'codex_app_password';
GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'%';
FLUSH PRIVILEGES;
```

The app auto-creates tables on startup.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open: <http://127.0.0.1:8000>

## Using `run_app.sh`

```bash
./run_app.sh
```

What it does:
1. Pull latest git changes
2. Install/update dependencies
3. Re-create the configured database
4. Ensure the configured app user exists with DB permissions
5. Start uvicorn

> Note: `run_app.sh` **drops and recreates** the configured database each run.
