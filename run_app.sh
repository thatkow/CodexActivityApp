#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "Pulling latest changes..."
git pull --rebase --autostash

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_ADMIN_USER="${MYSQL_ADMIN_USER:-root}"
MYSQL_ADMIN_PASSWORD="${MYSQL_ADMIN_PASSWORD:-}"
APP_DB_NAME="${APP_DB_NAME:-codex_activity_app}"
APP_DB_USER="${APP_DB_USER:-codex_app}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-codex_app_password}"

MYSQL_PWD="$MYSQL_ADMIN_PASSWORD" mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_ADMIN_USER" <<SQL
DROP DATABASE IF EXISTS \`$APP_DB_NAME\`;
CREATE DATABASE \`$APP_DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
DROP USER IF EXISTS '$APP_DB_USER'@'localhost';
CREATE USER '$APP_DB_USER'@'localhost' IDENTIFIED BY '$APP_DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$APP_DB_NAME\`.* TO '$APP_DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment in .venv..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

export DATABASE_URL="mysql+pymysql://$APP_DB_USER:$APP_DB_PASSWORD@$MYSQL_HOST/$APP_DB_NAME"

echo "Starting uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
