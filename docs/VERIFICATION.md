# Verified application checks

Executed in GitHub Codespaces at 2026-11-19T17:33:58.977976+00:00.

Source revision at collection: `d0fda59359b9cb40737441b69a03350b4427df23`. Model SHA-256: `b8b53a790a164593212647bd9f88ce352e70ca4460e1602e9880b71a7dfbc5a3`.

| Check | Outcome |
|---|---|
| Unit tests | 13 passed in 1.45s |
| Backend tests | 30 passed in 27.96s |
| React production build | Passed |
| Full browser journeys | All three passed |

- Browser journey passed: registration, profile, ML recommendations, connections, project applications, teams, two-user live chat, image/file uploads, private previews/downloads, retry deduplication, persistent attachment history, read receipts, events and mobile navigation.
- Presentation checks passed: real ML match, project match, ready connection, two-account live chat, activities and mobile layout.
- Survey UI, reciprocal explanations, measured results, mobile layout, null fields and invalid-number rejection passed.

Checks use a separate disposable MongoDB database, Redis database 15 and ports 8001/5174. The existing presentation database is not reset. Browser screenshots use fictional fixtures; statistical evaluation uses the verified real survey. Passing application tests does not establish social-outcome prediction quality.

Reproduce with `bash scripts/cloud-verify.sh`, then `.venv/bin/python scripts/collect-evidence.py`. See [testing instructions](TESTING.md).
