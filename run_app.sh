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

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_ROOT_USER="${MYSQL_ROOT_USER:-root}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-codex_activity_app}"
MYSQL_USER="${MYSQL_USER:-codex_app}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-codex_app_password}"

MYSQL_ROOT_ARGS=(-h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_ROOT_USER")
if [[ -n "$MYSQL_ROOT_PASSWORD" ]]; then
  MYSQL_ROOT_ARGS+=("-p$MYSQL_ROOT_PASSWORD")
fi

echo "Recreating database and app user..."
mysql "${MYSQL_ROOT_ARGS[@]}" <<SQL
DROP DATABASE IF EXISTS \\`$MYSQL_DATABASE\\`;
CREATE DATABASE \\`$MYSQL_DATABASE\\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD';
ALTER USER '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD';
GRANT ALL PRIVILEGES ON \\`$MYSQL_DATABASE\\`.* TO '$MYSQL_USER'@'%';
FLUSH PRIVILEGES;
SQL

echo "Starting uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
