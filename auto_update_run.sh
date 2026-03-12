#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
APP_MODULE="app:app"
HOST="0.0.0.0"
PORT="8000"
PULL_INTERVAL=10

cd "$REPO_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

install_requirements() {
  pip install --upgrade pip
  pip install -r requirements.txt
}

restart_uvicorn() {
  if [[ -n "${UVICORN_PID:-}" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
  fi

  pkill -f "uvicorn $APP_MODULE" 2>/dev/null || true

  uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" &
  UVICORN_PID=$!
  echo "Started uvicorn with PID $UVICORN_PID"
}

git pull
install_requirements
restart_uvicorn

while true; do
  sleep "$PULL_INTERVAL"

  old_head="$(git rev-parse HEAD)"
  git pull
  new_head="$(git rev-parse HEAD)"

  if [[ "$old_head" != "$new_head" ]]; then
    echo "Repository updated from $old_head to $new_head"
    install_requirements
    restart_uvicorn
  fi
done
