# connecT AI

An AI-powered university social and project collaboration platform. The current application has a React frontend, Django REST Framework API, MongoDB document storage, Random Forest student matching, K-Means candidate grouping, and Django Channels messaging. The earlier Flask demo remains available during migration.

## Current Features

- JWT signup/login and protected APIs.
- Student profiles with PDF/DOCX résumé suggestions, manual review, and save.
- Student-to-student recommendations: K-Means candidate grouping followed by Random Forest compatibility ranking, with feature-derived explanations.
- Project creation, applications, profile-to-project skill/domain recommendations, and project-specific teammate recommendations.
- Connection requests, events/attendance, feedback capture, conversation history, read receipts, and Channels WebSocket delivery.
- A reproducible synthetic Excel dataset and offline K-Means/Random Forest training scripts.

## WSL Setup

Run commands from this directory in WSL. Python packages install into the project-local `.venv`:

```bash
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env
```

Provide a reachable MongoDB deployment through `MONGODB_URI` and `MONGODB_DATABASE` in `.env`. MongoDB is not bundled with this repository. For production/multi-process Channels, configure `REDIS_URL`; without it, Channels uses an in-memory layer suitable only for local single-process development.

Start the Django ASGI backend:

```bash
cd backend
../.venv/bin/daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

The liveness endpoint is `http://127.0.0.1:8000/api/health/`. The readiness endpoint `http://127.0.0.1:8000/api/health/ready/` also pings MongoDB and returns `503` with a JSON explanation when the database is unavailable. The sign-in page checks readiness and displays this prerequisite before a login attempt.

Install Node.js LTS and npm inside WSL for a fresh checkout, then start the React app in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves `http://localhost:5173` and proxies `/api` and `/ws` to the backend. In the current WSL workspace, a verified Node 24 runtime is installed under the ignored `.tools/` directory for local builds; it is not committed. To use it in this checkout, add `.tools/node-v24.21.0-linux-x64/bin` to `PATH` before running npm. MongoDB is not installed in this WSL environment, so authenticated/database-backed browser workflows need a local MongoDB service or an Atlas URI.

## API Map

- `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/token/refresh/`
- `GET/PUT /api/profiles/me/`, `POST /api/profiles/resume-suggestions/`
- `GET/POST /api/projects/`, `POST /api/projects/{id}/applications/`
- `GET /api/projects/recommendations/`, `GET /api/projects/{id}/teammates/`
- `GET/POST /api/connections/`, `PATCH /api/connections/{id}/`
- `GET/POST /api/events/`, `POST /api/events/{id}/attendance/`
- `POST /api/feedback/`
- `GET/POST /api/conversations/`, `GET/POST/PATCH /api/conversations/{id}/messages/`
- `POST /api/conversations/{id}/websocket-ticket/`, WebSocket `/ws/conversations/{id}/`
- `GET /api/recommendations/users/`

All APIs use JSON except résumé suggestions, which accept multipart form uploads. User/project/message endpoints require a bearer access token.

## Validation and ML Training

```bash
.venv/bin/python backend/manage.py check
.venv/bin/python backend/manage.py test platform_api config
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python ml/train_student_clusters.py
.venv/bin/python ml/train_compatibility_model.py
```

Both datasets are synthetic. The Random Forest target is generated from an auditable weighted compatibility rule, so reported performance measures reproduction of that rule, not real-world student outcomes. Evaluation now holds out users rather than randomly splitting pairs: the latest run used 959 training pairs and 65 test pairs from 189 unseen users, with no user shared across the partitions. The held-out set is small (53 incompatible, 12 compatible) and currently scores 100%; treat this as prototype verification only. See [the dataset and evaluation note](docs/ml/phase1_dataset_design.md).

K-Means evaluates $k=2$ through $k=10$ using silhouette score and selected $k=6$ (0.524659) on the current 1,000 synthetic profiles. Cluster IDs are algorithmic group identifiers, not hard-coded domain labels.

## MongoDB Choice

The backend uses MongoDB's official `django-mongodb-backend` 5.2.x with Django 5.2.x and direct PyMongo collection operations for domain documents. MongoDB documents Django REST Framework support as partial; the API keeps its persistence operations explicit and avoids depending on complex ORM joins. Validate against a real MongoDB deployment before production.

## Earlier Flask Demo

The existing profile/recommendation demo remains runnable from the repository root with `.venv/bin/python server.py` at `http://127.0.0.1:5000/`. It uses SQLite and is retained only as a migration/demo path; the Django application is the target architecture.