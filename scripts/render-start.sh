#!/usr/bin/env bash
set -euo pipefail
# Index setup is idempotent. Training is deliberately absent from deployment startup.
python backend/manage.py setup_db
exec python -m uvicorn config.asgi:application --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --ws-max-size 16384 --no-access-log
