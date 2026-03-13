#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "Pulling latest changes..."
git pull --rebase --autostash

if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment in .venv..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Recreating database schema..."
python -c "from main import reset_database; reset_database(); print('Database schema reset complete.')"

echo "Starting uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
