# CodexActivityApp

Business-style FastAPI app with:
- Organisation-scoped login (`email + password + organisation`)
- Account creation with existing/new organisation
- Dashboard showing organisation members

## MySQL setup (localhost)
The app expects a local MySQL instance and uses these defaults:

- `MYSQL_HOST=127.0.0.1`
- `MYSQL_PORT=3306`
- `MYSQL_USER=root`
- `MYSQL_PASSWORD=root`
- `MYSQL_DB=codex_activity_app`

You can override these via environment variables.

### Example local MySQL preparation
```sql
CREATE USER 'root'@'localhost' IDENTIFIED BY 'root';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

## Run the app
Use the helper script:

```bash
./run_app.sh
```

What it does:
1. Pulls the latest git changes.
2. Creates `.venv` if missing and activates it.
3. Installs `requirements.txt`.
4. Recreates the app database schema (`python3 main.py --reset-db`).
5. Starts Uvicorn on `http://0.0.0.0:8000`.

> Warning: resetting the DB drops and recreates tables.

## Manual run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py --init-db
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
