# CodexActivityApp

A minimal FastAPI/uvicorn app that serves a simple page saying **"Codex built this!"**.

## Project files

- `app.py` - FastAPI application.
- `requirements.txt` - Python dependencies.
- `auto_update_run.sh` - Auto-update runner script that keeps pulling and restarting uvicorn when code changes.

## Setup with `venv`

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open: `http://127.0.0.1:8000`

## Auto-update and restart script

Use the included script to:

1. Run an initial `git pull`.
2. Activate `.venv` (creating it first if missing).
3. Start `uvicorn`.
4. Every 10 seconds, run `git pull` again.
5. If repository changes are detected, reinstall `requirements.txt`, stop the running `uvicorn`, and restart it.

Run it with:

```bash
./auto_update_run.sh
```

Stop it with `Ctrl+C`; the script traps exits and shuts down any running uvicorn process.
