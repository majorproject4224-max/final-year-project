# Verification

The automated workflow is [Project checks](https://github.com/majorproject4224-max/final-year-project/actions/workflows/ci.yml). It runs in GitHub's cloud environment. Application dependencies and the application are not required on the office laptop.

## What is tested

- Django system checks and public health/readiness behavior.
- Registration, weak/duplicate credentials, JWT rotation/reuse, logout and password-change revocation.
- Profile validation, contact visibility, anonymous access, pagination and malformed JSON.
- Project ownership, applications, completed-project feedback, invitations and concurrent approvals for the last slot.
- Multiple conversations per student, duplicate-safe message retries, history/read state, outsider access, removed connections, WebSocket origin validation and one-use tickets.
- All three recommendation types, cold start, missing artifacts, ordered scores and no classifier training during API requests.
- Excel/CSV loading, normalization, duplicate/reference validation, entity-disjoint splits, shared feature calculations, saved K-Means/RF inference and résumé parsing.
- React production build.
- Chromium journey through registration/profile, recommendations, connections, project application/team formation, two-user live chat, read receipts, events and mobile navigation.

These are functional checks. They are not a real-user study, penetration test, accessibility certification or production load test.

## Local or Codespaces commands

Only on a personal laptop or in Codespaces. Set `MONGODB_DATABASE=connect_ai_test`, `RUN_MONGO_TESTS=1`, `DJANGO_DEBUG=1`, `API_THROTTLING_ENABLED=0`, and a disposable MongoDB replica-set URI plus Redis URL. Database tests **drop that test database** before each case and refuse other database suffixes.

```bash
python dataset/generate_synthetic_datasets.py
python ml/train.py
python backend/manage.py check
python backend/manage.py test platform_api config --verbosity 2
python -m unittest discover -s tests -v
npm ci --prefix frontend
npm run build --prefix frontend
```

Use the virtual-environment Python path from SETUP if it is not activated.

The browser journey additionally needs Playwright/Chromium in the test environment, seeded fictional data and running backend/frontend processes. The exact setup is in `.github/workflows/ci.yml`; it includes clearly disposable CI-only credentials. Never use those credentials on a public deployment.

## Verified package checkpoint

[Run 44099277272](https://github.com/majorproject4224-max/final-year-project/actions/runs/44099277272) passed on 2026-11-17: 12 Django/API/Channels tests, 10 ML/resume tests, the React production build, the complete browser journey, and the same 10 model/preprocessing tests against the committed artifacts on Windows. Later source formatting does not change these test expectations; check the latest workflow for the final commit.

## Evidence and troubleshooting

Each successful backend test stage uploads `trained-model-and-datasets`: generated tables, bundle, metrics and the Linux dependency lock. Browser runs upload `browser-checks`: screenshots, trace and server logs. A failed browser run saves `failure.png` before exiting. Artifacts expire after seven days; selected demonstration screenshots and the trained artifacts are committed separately.

The first cloud passes uncovered missing test-package initialization, an incorrect authentication status code and accessible form-label wiring; fixes were made before final verification. The current workflow result is the authoritative status for the checked-out commit.

Model metrics and their exact provenance are in [RESULTS.md](RESULTS.md). No results should be copied from an older experiment or described as real-world accuracy.
