#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
UVICORN_CMD=(uvicorn app:app --host 0.0.0.0 --port 8000)
UVICORN_PID=""

cd "$PROJECT_DIR"

echo "Pulling latest changes..."
git pull --ff-only

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

install_requirements() {
  echo "Installing dependencies..."
  pip install -r requirements.txt
}

recreate_database() {
  echo "Recreating database schema..."
  python recreate_db.py
}

start_uvicorn() {
  echo "Starting uvicorn..."
  "${UVICORN_CMD[@]}" &
  UVICORN_PID=$!
}

stop_uvicorn() {
  if [[ -n "${UVICORN_PID}" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    echo "Stopping uvicorn (PID: $UVICORN_PID)..."
    kill "$UVICORN_PID"
    wait "$UVICORN_PID" 2>/dev/null || true
  fi
}

cleanup() {
  stop_uvicorn
}

trap cleanup EXIT INT TERM

install_requirements
recreate_database
start_uvicorn

while true; do
  sleep 10

  previous_rev="$(git rev-parse HEAD)"

  if git pull --ff-only; then
    current_rev="$(git rev-parse HEAD)"

    if [[ "$previous_rev" != "$current_rev" ]]; then
      echo "Repository updated. Reinstalling, recreating DB, and restarting uvicorn..."
      stop_uvicorn
      install_requirements
      recreate_database
      start_uvicorn
    fi
  else
    echo "git pull failed; keeping current server process running."
  fi
done
