# CodexActivityApp

A business-style FastAPI + MySQL web application.

## Pages and behavior

- `/` is now a landing dashboard with tiles to navigate to:
  - `/projects`
  - `/members`
- `/projects`:
  - table with columns **Name**, **Description**, **Date Created**
  - Add Project and Delete All buttons
  - menu item to go back to `/`
  - project rows are clickable to open `/projects/{id}`
- `/projects/{id}`:
  - shows project fields
  - shows a members table for the project
  - members are clickable to open `/members/{id}`
  - includes **Add Member via Lookup** for assigning existing members to the project
- `/members`:
  - table with columns **First-name**, **Middle-name**, **Last-name**, **Phone**, **Email**
  - Add Member and Delete All buttons
  - member rows are clickable to open `/members/{id}`
  - **Middle-name** and **Phone** are optional
- `/members/{id}`:
  - shows all member fields
  - shows a table of projects that member belongs to

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

3. (Optional) Override defaults with environment variables:

   ```bash
   export DB_HOST=127.0.0.1
   export DB_PORT=3306
   export DB_USER=codex_app
   export DB_PASSWORD=codex_app_password
   export DB_NAME=codex_activity_app
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

4. Initialize DB schema:

   ```bash
   python init_db.py
   ```

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`.

## Auto-update runner

```bash
./auto_update_run.sh
```

Script behavior:

1. Initial `git pull`
2. Ensure + activate `.venv`
3. Install requirements
4. Initialize DB schema
5. Start Uvicorn
6. Every 10s: `git pull`
7. If `HEAD` changed: reinstall requirements, recreate DB tables (`python init_db.py --recreate`), interrupt running Uvicorn, restart Uvicorn.

> Stop with `Ctrl+C`.
