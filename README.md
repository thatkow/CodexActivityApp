# CodexActivityApp

A FastAPI + MySQL business-style project tracker UI.

## Features

- `/` serves a business application interface with a projects table:
  - **Name**
  - **Description**
  - **Date Created**
- Top-right controls include:
  - **Add Project** button (opens dialog)
  - **Delete Selected** button
- New projects default **Date Created** to today's date.
- Data is stored in a local MySQL database.

## Project files

- `app.py` - FastAPI app and API endpoints.
- `static/index.html` - UI, styling, and browser-side logic.
- `recreate_db.py` - Drops/recreates DB tables used by the app.
- `requirements.txt` - Python dependencies.
- `auto_update_run.sh` - Auto pull/reload script.

## 1) MySQL setup (localhost)

Run these commands in MySQL as a privileged user (e.g. `root`):

```sql
CREATE DATABASE codex_activity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'localhost';
FLUSH PRIVILEGES;
```

If your app connects through `127.0.0.1`, also allow that host:

```sql
CREATE USER 'codex_app'@'127.0.0.1' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

## 2) Python setup with `venv`

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional DB env vars (defaults shown):

```bash
export DB_USER=codex_app
export DB_PASSWORD=codex_password
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=codex_activity
```

Create/recreate the schema:

```bash
python recreate_db.py
```

## 3) Run the app manually

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open: `http://127.0.0.1:8000`

## Auto-update/restart script

Run:

```bash
./auto_update_run.sh
```

The script will:

1. Perform an initial `git pull --ff-only`.
2. Ensure `.venv` exists and activate it.
3. Install/update dependencies from `requirements.txt`.
4. **Recreate the database schema** (`python recreate_db.py`).
5. Start `uvicorn`.
6. Every 10 seconds, run `git pull --ff-only`.
7. If code changes are detected, it will:
   - stop running `uvicorn`,
   - reinstall dependencies,
   - **recreate the database schema**,
   - restart `uvicorn`.

Use `Ctrl+C` to stop the script; it will also stop the running `uvicorn` process.
