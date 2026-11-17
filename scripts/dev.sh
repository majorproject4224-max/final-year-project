#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then echo "First run bash scripts/bootstrap.sh"; exit 1; fi
.venv/bin/python -m uvicorn config.asgi:application --app-dir backend --host 0.0.0.0 --port 8000 &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM
npm run dev --prefix frontend
