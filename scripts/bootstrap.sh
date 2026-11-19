#!/usr/bin/env bash
# Run in Codespaces or a configured Linux/macOS development environment.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
if [ ! -f .env ]; then cp .env.example .env; fi
if [ ! -f ml/models/survey-recommender.joblib ]; then
  .venv/bin/python -m pip install -r ml/requirements-training.txt
  .venv/bin/python -m ml.train --download
fi
echo "Dependencies are ready. Next: bash scripts/start-data.sh, then bash scripts/dev.sh"
