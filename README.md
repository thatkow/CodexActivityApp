# CodexActivityApp

A minimal FastAPI + Uvicorn web app that serves a page with:

> Codex built this!

## Requirements

- Python 3.10+
- `git`

## Setup (venv)

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

2. Activate the virtual environment:

   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the app manually

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open: `http://localhost:8000`

## Auto-update and auto-restart script

Use the provided script:

```bash
./auto_update_uvicorn.sh
```

What it does:

1. Runs an initial `git pull --ff-only`
2. Activates the virtual environment (`.venv` by default)
3. Installs `requirements.txt`
4. Starts Uvicorn
5. Every 10 seconds, runs `git pull --ff-only`
6. If new commits are detected, it reinstalls dependencies, stops any running Uvicorn instance for this app, and restarts Uvicorn

### Optional environment variables

- `VENV_DIR` (default: `.venv`)
- `APP_MODULE` (default: `main:app`)
- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)
- `CHECK_INTERVAL` (default: `10`)
