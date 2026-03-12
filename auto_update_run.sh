#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PID_FILE="$PROJECT_DIR/.uvicorn.pid"
CHECK_INTERVAL=10

cd "$PROJECT_DIR"

ensure_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

install_requirements() {
  pip install --upgrade pip
  pip install -r "$PROJECT_DIR/requirements.txt"
}

stop_uvicorn() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping uvicorn process $pid"
      kill "$pid"
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi

  pkill -f "uvicorn main:app" 2>/dev/null || true
}

start_uvicorn() {
  echo "Starting uvicorn..."
  uvicorn main:app --host 0.0.0.0 --port 8000 &
  echo $! > "$PID_FILE"
}

restart_uvicorn() {
  stop_uvicorn
  start_uvicorn
}

pull_and_maybe_update() {
  local before after
  before="$(git rev-parse HEAD)"

  git pull --ff-only

  after="$(git rev-parse HEAD)"

  if [[ "$before" != "$after" ]]; then
    echo "Repository updated: $before -> $after"
    install_requirements
    restart_uvicorn
  else
    echo "No new changes found."
  fi
}

main() {
  ensure_venv
  install_requirements

  git pull --ff-only
  restart_uvicorn

  while true; do
    sleep "$CHECK_INTERVAL"
    ensure_venv
    pull_and_maybe_update
  done
}

trap stop_uvicorn EXIT

main
