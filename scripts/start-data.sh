#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait
docker compose exec -T mongo mongosh --quiet --eval 'try { rs.status() } catch (e) { rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]}) }'
ready=0
for attempt in $(seq 1 30); do
  if docker compose exec -T mongo mongosh --quiet --eval 'if (!db.hello().isWritablePrimary) quit(1)'; then ready=1; break; fi
  sleep 2
done
if [ "$ready" != "1" ]; then echo "MongoDB did not become ready."; exit 1; fi
.venv/bin/python backend/manage.py setup_db
