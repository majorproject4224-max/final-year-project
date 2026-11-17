#!/usr/bin/env bash
# Run in Codespaces or a personal Linux/macOS computer, never on the office laptop.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
if [ ! -f .env ]; then cp .env.example .env; fi
if [ ! -f ml/models/recommender.joblib ]; then
  .venv/bin/python dataset/generate_synthetic_datasets.py
  .venv/bin/python ml/train.py
fi
echo "Dependencies are ready. Next: bash scripts/start-data.sh, then bash scripts/dev.sh"
