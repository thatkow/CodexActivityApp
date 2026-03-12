#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".git" ]; then
  echo "This script must be run from inside a git repository."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

install_requirements() {
  pip install -r requirements.txt
}

uvicorn_pid=""

stop_server() {
  if [ -n "$uvicorn_pid" ] && kill -0 "$uvicorn_pid" 2>/dev/null; then
    kill "$uvicorn_pid"
    wait "$uvicorn_pid" 2>/dev/null || true
  fi

  # Cleanup any lingering uvicorn processes started from this project.
  pkill -f "uvicorn app:app" 2>/dev/null || true
}

start_server() {
  stop_server
  uvicorn app:app --host 0.0.0.0 --port 8000 &
  uvicorn_pid=$!
  echo "Started uvicorn with PID $uvicorn_pid"
}

cleanup() {
  stop_server
}

trap cleanup EXIT INT TERM

echo "Running initial git pull..."
git pull --ff-only
install_requirements
start_server

while true; do
  sleep 10

  previous_head="$(git rev-parse HEAD)"
  git pull --ff-only
  install_requirements
  current_head="$(git rev-parse HEAD)"

  if [ "$previous_head" != "$current_head" ]; then
    echo "New changes detected. Restarting uvicorn..."
    start_server
  fi
done
