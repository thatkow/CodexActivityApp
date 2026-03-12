# CodexActivityApp

A FastAPI + MySQL business-style dashboard with **Projects**, **Organizations**, and **Members**.

## Features

- `/` dashboard tiles to:
  - `/projects`
  - `/organizations`
  - `/members`
- `/projects`
  - table entries open `/projects/{id}`
  - add/delete project
  - project form shows/selects organization ownership
- `/projects/{id}`
  - displays all project fields
  - shows project members table (members link to `/members/{id}`)
  - supports adding members via lookup
  - lookup rule:
    - if project has organization, only members in that organization are shown
    - if project has no organization, all members are shown
- `/members`
  - columns: First-name, Middle-name, Last-name, Phone, Email
  - add/delete member
  - Middle-name and Phone are optional
  - entries open `/members/{id}`
- `/members/{id}`
  - displays all member fields
  - shows projects where the member is assigned
- `/organizations`
  - Name, Address(optional), ABN(optional)
  - add/delete organization
- Member ↔ Organization is many-to-many.
- Project ↔ Member is many-to-many.
- Project → Organization is optional many-to-one.

## Setup

### 1) MySQL setup

```sql
CREATE DATABASE codex_activity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'localhost';
FLUSH PRIVILEGES;
```

If connecting through `127.0.0.1`:

```sql
CREATE USER 'codex_app'@'127.0.0.1' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### 2) Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional env vars:

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

### 3) Run app

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open: `http://127.0.0.1:8000`

## Auto-update script

```bash
./auto_update_run.sh
```

The script does initial `git pull`, venv setup, requirements install, DB recreation, uvicorn start, and every 10s checks for updates and restarts with DB recreation when changes are pulled.
