# CodexActivityApp

A business-style FastAPI + Uvicorn project dashboard.

At `/`, the app shows:
- a **Projects** table with columns **Name**, **Description**, and **Date Created**
- an **Add Project** button (top-right) that opens a dialog to create a project
- a **Delete Selected** button next to Add for deleting the currently selected project

The project data is stored in a local MySQL database.

## Requirements

- Python 3.10+
- MySQL (localhost)
- `git`

## MySQL setup (database + user)

Log into MySQL as root/admin and run:

```sql
CREATE DATABASE codex_activity_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'codex_app_user'@'localhost' IDENTIFIED BY 'codex_app_password';

GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app_user'@'localhost';
FLUSH PRIVILEGES;
```

## Setup with venv

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

2. Activate it:

   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set DB environment variables (optional if using defaults shown above):

   ```bash
   export DB_HOST=127.0.0.1
   export DB_PORT=3306
   export DB_NAME=codex_activity_app
   export DB_USER=codex_app_user
   export DB_PASSWORD=codex_app_password
   ```

## Run manually

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open: `http://localhost:8000`

## Auto-update + auto-restart runner

```bash
./auto_update_uvicorn.sh
```

What it does:
1. Runs an initial `git pull --ff-only`
2. Activates the virtual environment (`.venv` by default)
3. Installs `requirements.txt`
4. Starts Uvicorn
5. Every 10 seconds, runs `git pull --ff-only`
6. If new commits are detected, reinstalls requirements, stops running Uvicorn, and restarts it

### Runner environment variables

- `VENV_DIR` (default: `.venv`)
- `APP_MODULE` (default: `main:app`)
- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)
- `CHECK_INTERVAL` (default: `10`)

### Database environment variables used by app

- `DB_HOST` (default: `127.0.0.1`)
- `DB_PORT` (default: `3306`)
- `DB_NAME` (default: `codex_activity_app`)
- `DB_USER` (default: `codex_app_user`)
- `DB_PASSWORD` (default: `codex_app_password`)
