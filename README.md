# CodexActivityApp

Business-style FastAPI web application for managing projects.

## Features

- Home page (`/`) shows a project table with columns:
  - Name
  - Description
  - Date Created
- **Add Project** button in the top-right opens a dialog to create a project.
- **Delete Selected** button next to Add deletes checked projects.
- Data is persisted in a local MySQL database.

## 1) Create MySQL database and user (localhost)

Log in to MySQL as root/admin and run:

```sql
CREATE DATABASE codex_activity_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_password';
CREATE USER 'codex_app'@'127.0.0.1' IDENTIFIED BY 'codex_password';

GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'localhost';
GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

> You can customize credentials with environment variables:
> `APP_DB_USER`, `APP_DB_PASSWORD`, `APP_DB_HOST`, `APP_DB_PORT`, `APP_DB_NAME`.

## 2) Setup Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Run locally

```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open: http://127.0.0.1:8000/

## Auto update + auto restart runner

Run:

```bash
./auto_update_run.sh
```

The script will:
1. run an initial `git pull`
2. activate `.venv`
3. start `uvicorn main:app`
4. every 10 seconds, run `git pull`
5. restart uvicorn if new commits were pulled
6. stop any running uvicorn process on restart/exit

Stop with `Ctrl+C`.
