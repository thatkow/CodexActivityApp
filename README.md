# CodexActivityApp

A FastAPI + MySQL business-style dashboard with dedicated **Projects** and **Organization** sections.

## Features

- `/` dashboard page with tiles:
  - **Projects** (`/projects`)
  - **Organization** (`/organizations`)
- `/projects` page:
  - table columns: **Name**, **Description**, **Date Created**, **Organization**
  - top-right **Add Project** + **Delete Selected** buttons
  - add form defaults Date Created to today
  - projects can be assigned to an organization
  - menu item to go back to `/`
- `/organizations` page:
  - table columns: **Name**, **Address (optional)**, **ABN (optional)**
  - top-right **Add Organization** + **Delete Selected** buttons
  - organization rows link to `/organizations/{id}`
- `/organizations/{id}` page:
  - single **Create Project** button that opens a form dialog
  - created projects are automatically associated with that organization
- Organizations and projects are persisted to local MySQL.

## Project files

- `app.py` - FastAPI routes, SQLAlchemy models, API endpoints.
- `recreate_db.py` - drop/recreate schema tables.
- `static/home.html` - dashboard tiles page.
- `static/projects.html` - projects page.
- `static/organizations.html` - organizations page.
- `static/organization_detail.html` - organization detail + linked project creation.
- `static/styles.css` - shared app styling.
- `requirements.txt` - Python dependencies.
- `auto_update_run.sh` - auto pull/reload/recreate script.

## 1) MySQL setup (localhost)

Run these commands in MySQL as a privileged user (e.g. `root`):

```sql
CREATE DATABASE codex_activity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'localhost';
FLUSH PRIVILEGES;
```

If you connect through `127.0.0.1`, also grant that host:

```sql
CREATE USER 'codex_app'@'127.0.0.1' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

## 2) Python setup with `venv`

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

Create/recreate schema:

```bash
python recreate_db.py
```

## 3) Run manually

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`.

## Auto-update/restart script

Run:

```bash
./auto_update_run.sh
```

It performs initial `git pull`, venv activation, requirements install, DB recreation, and uvicorn launch. Every 10 seconds it pulls changes; on new commits it stops uvicorn, reinstalls dependencies, recreates DB, and restarts uvicorn.
