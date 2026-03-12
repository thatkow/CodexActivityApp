# CodexActivityApp

A simple FastAPI app served by Uvicorn.

## App behavior

The root endpoint returns:

```json
{"message": "Codex built this!"}
```

## Local setup (venv)

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
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Run the app

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000`.

## Auto-update runner script

Use the included script to keep the app updated and restarted automatically:

```bash
./auto_update_run.sh
```

What it does:

1. Runs `git pull --ff-only`.
2. Ensures `.venv` exists and is activated.
3. Installs `requirements.txt`.
4. Stops any running `uvicorn main:app` process.
5. Starts Uvicorn.
6. Every 10 seconds, runs `git pull --ff-only`.
   - If there are new commits, it reinstalls requirements and restarts Uvicorn.
   - If no changes are found, it keeps the current process running.

To stop it, press `Ctrl+C`.
