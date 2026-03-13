# CodexActivityApp

A small FastAPI business portal with organisation-aware login and member directory.

## Features

- Login requires **organisation + email + password**.
- Account creation supports selecting an existing organisation or creating a new one.
- MySQL-backed entities:
  - `organisation(id, name)`
  - `users(id, email, hashed_pw, organisation_id)`
- Post-login dashboard shows:
  - `Organisation: <name>`
  - `Welcome <email>`
  - `Members` list for the same organisation.
- Logout action clears the session.

## Database setup (MySQL)

The app defaults to this DSN:

`mysql+pymysql://codex_app:codex_app_password@127.0.0.1:3306/codex_activity_app`

Create a dedicated MySQL database and user:

```sql
CREATE DATABASE codex_activity_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'codex_app'@'localhost' IDENTIFIED BY 'codex_app_password';
GRANT ALL PRIVILEGES ON codex_activity_app.* TO 'codex_app'@'localhost';
FLUSH PRIVILEGES;
```

If needed, override connection string:

```bash
export DATABASE_URL="mysql+pymysql://<user>:<password>@<host>:3306/<database>"
```

Also set a secure session secret in non-local environments:

```bash
export SESSION_SECRET="replace-with-a-long-random-value"
```

## Local run

```bash
chmod +x run_app.sh
./run_app.sh
```

`run_app.sh` now:
1. pulls latest changes,
2. installs dependencies,
3. **recreates the database schema** by dropping/creating tables,
4. launches uvicorn.

> Warning: schema recreation deletes existing data.

## Password hashing note

The app uses salted `pbkdf2_sha256` password hashing from Python's standard library, which avoids bcrypt backend compatibility issues and supports long passwords safely.
