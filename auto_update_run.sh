#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${REPO_DIR}/.venv"
APP_MODULE="main:app"
HOST="0.0.0.0"
PORT="8000"
POLL_SECONDS=10
UVICORN_PID=""

stop_uvicorn() {
  if [[ -n "${UVICORN_PID}" ]] && kill -0 "${UVICORN_PID}" 2>/dev/null; then
    echo "Stopping uvicorn (PID ${UVICORN_PID})"
    kill "${UVICORN_PID}" 2>/dev/null || true
    wait "${UVICORN_PID}" 2>/dev/null || true
  fi

  UVICORN_PID=""
}

start_uvicorn() {
  echo "Starting uvicorn on ${HOST}:${PORT}"
  uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" &
  UVICORN_PID=$!
}

cleanup() {
  stop_uvicorn
}

trap cleanup EXIT INT TERM

cd "${REPO_DIR}"

echo "Running initial git pull"
git pull --ff-only

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Virtual environment not found at ${VENV_DIR}"
  echo "Create it first with: python3 -m venv .venv"
  exit 1
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found in virtual environment. Install dependencies with: pip install -r requirements.txt"
  exit 1
fi

start_uvicorn
last_head="$(git rev-parse HEAD)"

while true; do
  sleep "${POLL_SECONDS}"

  echo "Checking for updates..."
  git pull --ff-only
  current_head="$(git rev-parse HEAD)"

  if [[ "${current_head}" != "${last_head}" ]]; then
    echo "New commit detected. Restarting uvicorn..."
    stop_uvicorn
    start_uvicorn
    last_head="${current_head}"
  fi

done
