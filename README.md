# CodexActivityApp

Business-style FastAPI app with MySQL-backed **Projects** and **Members** management.

## Pages

- `/` home page with tiles linking to Projects and Members
- `/projects` table of projects with add/delete actions
- `/projects/{id}` project detail page with fields + member list + member lookup add
- `/members` table of members with add/delete actions
- `/members/{id}` member detail page with fields + projects table

## MySQL setup

Run in MySQL as root/admin:

```sql
CREATE DATABASE codex_activity_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'codex_app_user'@'localhost' IDENTIFIED BY 'codex_app_password';
GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app_user'@'localhost';
FLUSH PRIVILEGES;
```

Tables are auto-created at app startup:
- `projects`
- `members`
- `project_members` (join table)

## Setup (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional DB env vars (defaults shown):

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=codex_activity_app
export DB_USER=codex_app_user
export DB_PASSWORD=codex_app_password
```

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open: <http://localhost:8000>

## Auto-update runner

```bash
./auto_update_uvicorn.sh
```

It performs initial `git pull --ff-only`, activates venv, installs dependencies, starts uvicorn, and every 10 seconds pulls again; on new commits it reinstalls requirements and restarts uvicorn.
