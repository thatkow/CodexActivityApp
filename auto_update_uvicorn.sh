#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
APP_MODULE="${APP_MODULE:-main:app}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Virtual environment not found at $VENV_DIR"
  echo "Create it first: python3 -m venv $VENV_DIR"
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

UVICORN_PID=""

stop_uvicorn() {
  if [[ -n "${UVICORN_PID:-}" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    echo "Stopping uvicorn (pid: $UVICORN_PID)"
    kill "$UVICORN_PID"
    wait "$UVICORN_PID" 2>/dev/null || true
  fi

  pkill -f "uvicorn $APP_MODULE" 2>/dev/null || true
}

start_uvicorn() {
  echo "Starting uvicorn at http://$HOST:$PORT"
  uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" &
  UVICORN_PID=$!
}

cleanup() {
  stop_uvicorn
}

trap cleanup EXIT INT TERM

echo "Initial git pull..."
git pull --ff-only

echo "Installing/updating dependencies..."
pip install -r requirements.txt

start_uvicorn

while true; do
  sleep "$CHECK_INTERVAL"

  PREV_HEAD="$(git rev-parse HEAD)"
  echo "Checking for updates..."
  git pull --ff-only
  NEW_HEAD="$(git rev-parse HEAD)"

  if [[ "$PREV_HEAD" != "$NEW_HEAD" ]]; then
    echo "Repository changed. Reinstalling dependencies and restarting uvicorn..."
    pip install -r requirements.txt
    stop_uvicorn
    start_uvicorn
  else
    echo "No changes detected."
  fi
done
