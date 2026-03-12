#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

BEFORE_HEAD="$(git rev-parse HEAD)"

git pull --ff-only

AFTER_HEAD="$(git rev-parse HEAD)"

if [[ "$BEFORE_HEAD" == "$AFTER_HEAD" ]]; then
  echo "No changes pulled. Nothing to do."
  exit 0
fi

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv directory. Create one before running this script."
  exit 1
fi

source .venv/bin/activate
pip install -r requirements.txt

if pgrep -f "uvicorn main:app" >/dev/null; then
  pkill -f "uvicorn main:app"
fi

nohup uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &

echo "Changes deployed. Uvicorn restarted in the background."
