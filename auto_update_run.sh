#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Error: .venv directory not found. Create it first (python -m venv .venv)."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

UVICORN_PID=""

stop_uvicorn() {
  if [[ -n "${UVICORN_PID}" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    echo "Stopping uvicorn (pid: ${UVICORN_PID})"
    kill "$UVICORN_PID"
    wait "$UVICORN_PID" 2>/dev/null || true
  fi

  # In case uvicorn is running from another stale invocation in this repo.
  pkill -f "uvicorn main:app" 2>/dev/null || true
}

start_uvicorn() {
  echo "Starting uvicorn..."
  uvicorn main:app --host 0.0.0.0 --port 8000 &
  UVICORN_PID=$!
  echo "uvicorn started with pid: ${UVICORN_PID}"
}

cleanup() {
  stop_uvicorn
}

trap cleanup EXIT INT TERM

echo "Initial git pull..."
git pull
start_uvicorn

while true; do
  sleep 10

  CURRENT_HEAD="$(git rev-parse HEAD)"
  echo "Checking for updates (git pull)..."
  git pull
  NEW_HEAD="$(git rev-parse HEAD)"

  if [[ "$CURRENT_HEAD" != "$NEW_HEAD" ]]; then
    echo "Changes detected. Restarting uvicorn..."
    stop_uvicorn
    start_uvicorn
  else
    echo "No changes detected."
  fi
done
