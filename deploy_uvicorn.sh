#!/usr/bin/env bash
set -euo pipefail

FORCE=0
if [[ "${1:-}" == "-f" ]]; then
  FORCE=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [-f]"
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
REQ_FILE="$REPO_DIR/requirements.txt"
APP_MODULE="main:app"
HOST="0.0.0.0"
PORT="8000"
PID_FILE="$REPO_DIR/.uvicorn.pid"
LOG_FILE="$REPO_DIR/uvicorn.log"

cd "$REPO_DIR"

CURRENT_HEAD="$(git rev-parse HEAD)"
git pull --ff-only
NEW_HEAD="$(git rev-parse HEAD)"

if [[ $FORCE -eq 0 && "$CURRENT_HEAD" == "$NEW_HEAD" ]]; then
  echo "No repository changes detected. Use -f to force deployment steps."
  exit 0
fi

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$REQ_FILE"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE")"
  if kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID"
    sleep 1
  fi
  rm -f "$PID_FILE"
fi

nohup uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "uvicorn restarted in the background (PID: $NEW_PID)"
