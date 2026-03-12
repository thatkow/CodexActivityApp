# CodexActivityApp

A business-style FastAPI web app served by uvicorn with MySQL persistence.

## Features

- Landing page (`/`) with navigation tiles.
- Projects page (`/projects`) with:
  - table columns **Name**, **Description**, **Organization**, **Date Created**
  - **Add Project** dialog (including organization selection)
  - **Delete Selected** action
  - clickable project entries to project detail pages
- Members page (`/members`) with:
  - table columns **First-name**, **Middle-name** (optional), **Last-name**, **Phone** (optional), **Email**
  - **Add Member** dialog
  - **Import CSV** button/dialog for CSV with columns `First-name,Middle-name,Last-name,Phone,Email`
  - **Delete Selected** action
  - clickable member entries to member detail pages
- Organization page (`/organizations`) with:
  - table columns **Name**, **Address** (optional), **ABN** (optional)
  - **Add Organization** dialog
  - **Delete Selected** action
  - clickable organization entries to organization detail pages
- Organization detail page (`/organizations/{id}`):
  - create a project directly in that organization (auto-assigned association)
  - view organization projects
  - add members to organization (many-to-many lookup)
- Project detail page (`/projects/{id}`) showing project fields including organization and project members.
- Member detail page (`/members/{id}`) showing member fields, projects, and associated organizations.

## 1) Create MySQL database and user

Use a MySQL admin account and run:

```sql
CREATE DATABASE codex_activity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_password';
GRANT ALL PRIVILEGES ON codex_activity.* TO 'codex_app'@'localhost';
FLUSH PRIVILEGES;
```

## 2) Python setup with venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Configure DB connection (optional)

Defaults are shown in parentheses:

- `DB_HOST` (`127.0.0.1`)
- `DB_PORT` (`3306`)
- `DB_USER` (`codex_app`)
- `DB_PASSWORD` (`codex_password`)
- `DB_NAME` (`codex_activity`)

Example:

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=codex_app
export DB_PASSWORD=codex_password
export DB_NAME=codex_activity
```

## 4) Configure `.env` (including SMTP)

The app loads environment variables from a `.env` file at startup.

Example `.env`:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=codex_app
DB_PASSWORD=codex_password
DB_NAME=codex_activity

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=no-reply@example.com
SMTP_USE_TLS=true
APP_BASE_URL=http://127.0.0.1:8000
```

SMTP variables are used when adding/removing a member from a project:

- `SMTP_HOST` (required to enable email sending)
- `SMTP_PORT` (default `587`)
- `SMTP_USER` (optional)
- `SMTP_PASSWORD` (optional)
- `SMTP_FROM` (required to enable email sending)
- `SMTP_USE_TLS` (`true`/`false`, default `true`)
- `APP_BASE_URL` (default `http://127.0.0.1:8000`, used to generate project links in emails)

## 5) Run locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`.

## Auto-update runner

`auto_update_run.sh` behavior:

1. Runs `git pull --ff-only`.
2. Activates `.venv`.
3. Stops running uvicorn for this app, then starts it.
4. Every 10 seconds: runs `git pull --ff-only`.
5. If commit hash changed, restarts uvicorn.

Usage:

```bash
chmod +x auto_update_run.sh
./auto_update_run.sh
```
