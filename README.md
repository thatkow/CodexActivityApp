# CodexActivityApp

A small business-style FastAPI web app served by uvicorn that manages a portfolio of projects.

## Features

- Dashboard-style UI with a business application look and feel.
- Project table on `/` with columns:
  - **Name**
  - **Description**
  - **Date Created**
- **Add Project** button (top-right) that opens a dialog for creating a project.
- **Delete Selected** button next to Add Project for deleting checked rows.
- Data persisted in a localhost MySQL database.

## 1) Create MySQL database and user

Use a MySQL account with permission to create users/databases, then run:

```sql
CREATE DATABASE codex_activity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'localhost';
FLUSH PRIVILEGES;
```

> You can change these values; if you do, set matching environment variables before starting the app.

## 2) Python setup with venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Configure database connection (optional if using defaults)

The app reads these environment variables:

- `DB_HOST` (default: `127.0.0.1`)
- `DB_PORT` (default: `3306`)
- `DB_USER` (default: `codex_app`)
- `DB_PASSWORD` (default: `codex_password`)
- `DB_NAME` (default: `codex_activity`)

Example:

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=codex_app
export DB_PASSWORD=codex_password
export DB_NAME=codex_activity
```

## 4) Run locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

## Auto-update runner

`auto_update_run.sh` keeps the app synced with git and restarts uvicorn when updates arrive.

Behavior:

1. Runs initial `git pull --ff-only`.
2. Activates `.venv`.
3. Stops any running uvicorn instance for `main:app`.
4. Starts uvicorn.
5. Every 10 seconds, runs `git pull --ff-only`.
6. If the checked-out commit changed, stops uvicorn and restarts it.

Usage:

```bash
chmod +x auto_update_run.sh
./auto_update_run.sh
```

Stop with `Ctrl+C`.
