#!/usr/bin/env bash
set -euo pipefail

before_pull="$(git rev-parse HEAD)"
git pull

after_pull="$(git rev-parse HEAD)"

if [[ "$before_pull" != "$after_pull" ]]; then
  echo "Repository updated. Preparing environment and starting uvicorn..."

  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate

  pip install -r requirements.txt
  uvicorn main:app --host 0.0.0.0 --port 8000
else
  echo "No new changes pulled. Exiting without starting uvicorn."
fi
