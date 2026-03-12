#!/usr/bin/env bash
set -euo pipefail

FORCE=false
if [[ "${1:-}" == "-f" ]]; then
  FORCE=true
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if [[ ! -d .git ]]; then
  echo "Error: $REPO_DIR is not a git repository."
  exit 1
fi

before_head="$(git rev-parse HEAD)"
git pull
after_head="$(git rev-parse HEAD)"

if [[ "$FORCE" != true && "$before_head" == "$after_head" ]]; then
  echo "No changes detected after git pull. Nothing to do. Use -f to force deployment steps."
  exit 0
fi

if [[ ! -d venv ]]; then
  echo "Error: venv directory not found at $REPO_DIR/venv"
  exit 1
fi

# shellcheck source=/dev/null
source "$REPO_DIR/venv/bin/activate"

pip install -r requirements.txt

pkill -f "uvicorn main:app" || true

nohup uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &

echo "Uvicorn restarted in the background (PID: $!)."
