# CodexActivityApp

A FastAPI business portal with:
- organisation-aware login (`email`, `password`, `organisation`)
- account creation with existing organisation selection or new organisation creation
- MySQL-backed one-to-many `Organisation -> Users` model
- bcrypt password hashing
- organisation dashboard showing members and logout

## 1) Create local MySQL database and app user

Run the following as a MySQL admin user:

```sql
CREATE DATABASE codex_activity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codexapp'@'localhost' IDENTIFIED BY 'codexpass';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codexapp'@'localhost';
FLUSH PRIVILEGES;
```

If your MySQL is bound to `127.0.0.1`, also create/grant for that host:

```sql
CREATE USER 'codexapp'@'127.0.0.1' IDENTIFIED BY 'codexpass';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codexapp'@'127.0.0.1';
FLUSH PRIVILEGES;
```

## 2) Configure environment variables (optional)

Defaults are:
- `DB_HOST=127.0.0.1`
- `DB_PORT=3306`
- `DB_NAME=codex_activity`
- `DB_USER=codexapp`
- `DB_PASSWORD=codexpass`
- `SESSION_SECRET=change-me-in-production`

You can override these before running uvicorn.

## 3) Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python init_db.py --recreate
uvicorn main:app --reload
```

Then open <http://127.0.0.1:8000>.

## Deploy/update script

`./deploy_uvicorn.sh`
- runs `git pull --ff-only`
- if there are changes (or when `-f` is used), ensures `.venv`, installs dependencies,
  **re-creates database tables**, and restarts uvicorn in background

Force all steps regardless of git changes:

```bash
./deploy_uvicorn.sh -f
```
