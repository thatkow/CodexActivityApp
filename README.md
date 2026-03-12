# CodexActivityApp

A minimal FastAPI app served by Uvicorn.

## App behavior

- `GET /` returns:

```json
{"message": "Codex built this!"}
```

## Local setup (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```bash
source .venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open <http://127.0.0.1:8000>.

## Auto-update runner

Use `auto_update_uvicorn.sh` to keep the app synced with git and restarted when code changes.

```bash
./auto_update_uvicorn.sh
```

What it does:

1. Runs an initial `git pull --ff-only`.
2. Creates and activates `.venv` (if missing).
3. Runs `pip install -r requirements.txt`.
4. Starts `uvicorn app:app`.
5. Every 10 seconds, it:
   - Runs `git pull --ff-only`.
   - Runs `pip install -r requirements.txt` after each pull.
   - Checks for new commits and restarts Uvicorn if changes were pulled.
6. Stops any running Uvicorn process before restarting.
