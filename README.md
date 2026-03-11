# CodexActivityApp

A tiny FastAPI app served by uvicorn.

## App behavior

The root route (`/`) renders a simple message:

- `Codex built this!`

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run locally

Start the app with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then visit `http://localhost:8000`.

## Auto-update runner

Use `auto_update_run.sh` to keep the server updated automatically.

What it does:

1. Runs an initial `git pull --ff-only`.
2. Activates `.venv`.
3. Starts uvicorn for this project.
4. Every 10 seconds, runs `git pull --ff-only`.
5. If the checked-out commit changed, it stops the running uvicorn process and starts it again.

Run it with:

```bash
chmod +x auto_update_run.sh
./auto_update_run.sh
```

Stop it with `Ctrl+C`.
