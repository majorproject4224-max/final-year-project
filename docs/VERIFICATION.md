# Verified application checks

Executed in GitHub Codespaces at 2026-11-19T15:25:36.466087+00:00.

Source revision at collection: `dc3e94c6c5ceaaab91ca8f22057e3e45557192ad`. Model SHA-256: `06a19c12016c3c92281d206aa65a296eeb8569de495068b0a5260914a84908b8`.

| Check | Outcome |
|---|---|
| Unit tests | 11 passed in 1.62s |
| Backend tests | 25 passed in 28.85s |
| React production build | Passed |
| Full browser journeys | All three passed |

- Browser journey passed: registration, profile, ML recommendations, connections, project applications, teams, two-user live chat, image/file uploads, private previews/downloads, retry deduplication, persistent attachment history, read receipts, events and mobile navigation.
- Presentation checks passed: real ML match, project match, ready connection, two-account live chat, activities and mobile layout.
- Survey UI, reciprocal explanations, measured results, mobile layout, null fields and invalid-number rejection passed.

Checks use a separate disposable MongoDB database, Redis database 15 and ports 8001/5174. The existing presentation database is not reset. Browser screenshots use fictional fixtures; statistical evaluation uses the verified real survey. Passing application tests does not establish social-outcome prediction quality.

Reproduce with `bash scripts/cloud-verify.sh`, then `.venv/bin/python scripts/collect-evidence.py`. See [testing instructions](TESTING.md).
