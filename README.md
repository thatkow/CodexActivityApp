# CodexActivityApp

A FastAPI business-style login application with MySQL-backed organisations and users.

## Features
- Login with **organisation + email + password**
- Create account flow that lets users:
  - Select an existing organisation
  - Or create a new organisation
- Session-based authentication
- Post-login dashboard:
  - `Organisation: <name>` title
  - `Welcome <email>`
  - `Members` list for that organisation
  - Logout button

## Data model
The app uses MySQL with these entities:

- `organisation`
  - `id`
  - `name`
- `users`
  - `id`
  - `email`
  - `hashed_pw`
  - `organisation_id` (many users belong to one organisation)

## Local setup
1. Ensure MySQL is running on localhost.
2. Create a non-root admin user that can create databases/users (example):

```sql
CREATE USER 'codex_admin'@'localhost' IDENTIFIED BY 'codex_admin_password';
GRANT CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE USER, GRANT OPTION ON *.* TO 'codex_admin'@'localhost';
FLUSH PRIVILEGES;
```

> You can also use an existing privileged MySQL account (not root recommended for app runtime).

3. Start the app using the launcher script:

```bash
MYSQL_ADMIN_USER=codex_admin \
MYSQL_ADMIN_PASSWORD=codex_admin_password \
APP_DB_USER=codex_app \
APP_DB_PASSWORD=codex_app_password \
./run_app.sh
```

`run_app.sh` will:
- pull latest code
- recreate the database from scratch (`DROP DATABASE` + `CREATE DATABASE`)
- recreate the app DB user (non-root)
- install dependencies
- launch uvicorn

## Environment variables
- `MYSQL_HOST` (default `localhost`)
- `MYSQL_PORT` (default `3306`)
- `MYSQL_ADMIN_USER` (default `root`)
- `MYSQL_ADMIN_PASSWORD` (default empty)
- `APP_DB_NAME` (default `codex_activity_app`)
- `APP_DB_USER` (default `codex_app`)
- `APP_DB_PASSWORD` (default `codex_app_password`)
- `SESSION_SECRET` (default `dev-only-secret-change-me`)

The app runtime DB URL is composed automatically by `run_app.sh` as:

`mysql+pymysql://<APP_DB_USER>:<APP_DB_PASSWORD>@<MYSQL_HOST>/<APP_DB_NAME>`

## Run directly without script (optional)
If you manually prepared MySQL:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='mysql+pymysql://codex_app:codex_app_password@localhost/codex_activity_app'
uvicorn main:app --reload
```
