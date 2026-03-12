# CodexActivityApp

A business-style FastAPI web application backed by MySQL.

## Features

- `/` shows a **Projects** dashboard table with columns:
  - Name
  - Description
  - Date Created
- **Add Project** button (top-right above the table) opens a dialog form.
- Dialog defaults **Date Created** to today's date.
- **Delete All** button is shown next to Add Project.
- Each project row also includes a Delete button.

## MySQL setup (localhost)

1. Log into local MySQL as root (or another admin user):

   ```bash
   mysql -u root -p
   ```

2. Create a dedicated database and user:

   ```sql
   CREATE DATABASE codex_activity_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_app_password';
   GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. (Optional) If you want to run the app with custom credentials, set env vars:

   ```bash
   export DB_HOST=127.0.0.1
   export DB_PORT=3306
   export DB_USER=codex_app
   export DB_PASSWORD=codex_app_password
   export DB_NAME=codex_activity_app
   ```

## Setup with `venv`

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

4. Initialize database tables:

   ```bash
   python init_db.py
   ```

## Run the app

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`.

## Auto-update runner script

Run:

```bash
./auto_update_run.sh
```

What it does:

1. Runs `git pull` once at startup.
2. Ensures `.venv` exists and is activated.
3. Installs/upgrades from `requirements.txt`.
4. Initializes the database.
5. Starts Uvicorn.
6. Every 10 seconds, runs `git pull` again.
7. If git `HEAD` changed, it:
   - reinstalls dependencies,
   - **recreates the projects database table** (`python init_db.py --recreate`),
   - interrupts running Uvicorn,
   - restarts Uvicorn.

> Stop the script with `Ctrl+C`.
