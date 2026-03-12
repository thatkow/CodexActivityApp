# CodexActivityApp

A minimal FastAPI app served by Uvicorn.

## App behavior

- Visiting `/` returns a simple page that says: **"Codex built this!"**

## Setup with `venv`

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

2. Activate it:

   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the app

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`.

## Auto-update runner script

Use the script below to keep the app synced with git and automatically restart Uvicorn when changes are pulled:

```bash
./auto_update_run.sh
```

What it does:

1. Runs `git pull` once at startup.
2. Ensures `.venv` exists and is activated.
3. Installs/upgrades `requirements.txt`.
4. Starts Uvicorn.
5. Every 10 seconds, runs `git pull` again.
6. If the git `HEAD` changed, reinstalls dependencies and restarts Uvicorn.
7. Before restarting, it interrupts any existing Uvicorn process started for this app.

> Stop the script with `Ctrl+C`.
