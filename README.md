# CodexActivityApp

A minimal FastAPI app served with Uvicorn.

## App behavior

The root endpoint returns:

```json
{"message": "Codex built this!"}
```

## Setup (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run locally

```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://127.0.0.1:8000/`.

## Auto-update + auto-restart runner

Use the provided script to keep the app synced to git and restarted when updates are pulled:

```bash
./auto_update_run.sh
```

What it does:
1. Runs an initial `git pull`.
2. Activates `.venv`.
3. Starts `uvicorn main:app`.
4. Every 10 seconds, runs `git pull` again.
5. If `HEAD` changed, it stops the running uvicorn process and starts it again.

Stop it with `Ctrl+C`.
