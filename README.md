# CodexActivityApp

A FastAPI + MySQL business-style web app for tracking projects.

## Features

- Project table at `/` with columns:
  - Name
  - Description
  - Date Created
- Toolbar buttons above the table:
  - Add
  - Edit
  - Delete
- Modal dialog for create/edit (Date Created defaults to today's date for new records).
- Persistent storage in local MySQL.

## 1) MySQL setup (localhost)

Run these commands in MySQL as an admin user (for example `root`):

```sql
CREATE DATABASE codex_activity_app;
CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'localhost';
FLUSH PRIVILEGES;
```

If your MySQL server is only bound to TCP localhost and not socket auth, use `127.0.0.1` in app config (this project defaults to that).

## 2) Python venv setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Initialize database schema

```bash
python init_db.py
```

This creates the `projects` table if it does not exist.

## 4) Run the app

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open: `http://localhost:8000`

## Environment variables

Defaults are provided, but you can override:

- `DB_HOST` (default: `127.0.0.1`)
- `DB_PORT` (default: `3306`)
- `DB_NAME` (default: `codex_activity_app`)
- `DB_USER` (default: `codex_app`)
- `DB_PASSWORD` (default: `codex_password`)

## Auto-update runner script

Run:

```bash
./auto_update_run.sh
```

Behavior:

1. Performs initial `git pull --ff-only`.
2. Creates/activates `.venv`.
3. Installs `requirements.txt`.
4. Initializes database schema (`python init_db.py`).
5. Stops any running `uvicorn main:app` process.
6. Starts Uvicorn.
7. Every 10 seconds:
   - Runs `git pull --ff-only`.
   - If commits changed, it:
     - reinstalls dependencies,
     - **recreates the projects table** (`python init_db.py --recreate`),
     - restarts Uvicorn.

Press `Ctrl+C` to stop.
