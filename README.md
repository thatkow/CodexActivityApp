# CodexActivityApp

Business-style FastAPI app with MySQL-backed **Projects**, **Members**, and **Organizations**.

## Pages

- `/` home page with tiles linking to Projects, Members, and Organization
- `/projects` projects table with add/delete and organization selection in the form
- `/projects/{id}` project detail showing fields, organization, and members
  - if the project has an organization, only members in that organization are shown/selectable
  - if no organization, all members are available
- `/members` members table with add/delete actions
- `/members/{id}` member detail page with fields, projects, and organizations
- `/organizations` organizations table with add/delete actions
- `/organizations/{id}` organization detail with:
  - one **Create Project** button that opens a form (project auto-linked to this org)
  - members table and member lookup association

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
- `organizations`
- `project_members` (many-to-many)
- `organization_members` (many-to-many)

On startup, the app also performs a lightweight compatibility migration for older databases by adding `projects.organization_id` if it is missing.

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
