#!/usr/bin/env bash
# Codespaces only; separate disposable database, Redis database and server ports.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY -c 'from playwright.sync_api import sync_playwright' || { echo "In Codespaces, install Playwright and Chromium as documented in docs/TESTING.md."; exit 1; }
export DJANGO_DEBUG=1 API_THROTTLING_ENABLED=0
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver
export MONGODB_DATABASE="connect_ai_verify_$(date +%Y%m%d%H%M%S)_test"
export REDIS_URL=redis://127.0.0.1:6379/15
export FRONTEND_URL=http://127.0.0.1:5173/
export CORS_ALLOWED_ORIGINS=http://127.0.0.1:5174
export E2E_BASE_URL=http://127.0.0.1:5174
export E2E_API_URL=http://127.0.0.1:8001/api
export E2E_PASSWORD="${E2E_PASSWORD:-disposable-browser-test-only-4224!}"
for port in 8001 5174; do
  if curl -sS --max-time 2 "http://127.0.0.1:$port/" >/dev/null 2>&1; then
    echo "Port $port is occupied. Stop the previous test server before verification."; exit 1
  fi
done
mkdir -p test-results
$PY -m unittest discover -s tests -v > test-results/unit.log 2>&1
RUN_MONGO_TESTS=1 $PY backend/manage.py test platform_api config --verbosity 2 > test-results/backend.log 2>&1
npm run build --prefix frontend > test-results/build.log 2>&1
$PY backend/manage.py setup_db
DEMO_PASSWORD="$E2E_PASSWORD" $PY backend/manage.py prepare_presentation --apply --password-env DEMO_PASSWORD
$PY -m uvicorn config.asgi:application --app-dir backend --host 127.0.0.1 --port 8001 > test-results/backend-server.log 2>&1 &
backend_pid=$!
DEV_API_TARGET=http://127.0.0.1:8001 node frontend/node_modules/vite/bin/vite.js frontend --host 127.0.0.1 --port 5174 > test-results/frontend-server.log 2>&1 &
frontend_pid=$!
trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' EXIT INT TERM
for attempt in $(seq 1 30); do
  kill -0 "$backend_pid" "$frontend_pid" || { echo "A test server stopped unexpectedly."; exit 1; }
  if curl -fsS http://127.0.0.1:8001/api/health/ >/dev/null && curl -fsS "$E2E_BASE_URL" >/dev/null; then break; fi
  sleep 2
done
$PY tests/browser_journey.py > test-results/browser.log 2>&1
$PY tests/presentation_browser.py > test-results/presentation-browser.log 2>&1
$PY tests/survey_browser.py > test-results/survey-browser.log 2>&1
echo "All cloud verification checks passed. Evidence is in test-results/."
