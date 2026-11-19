# Verification in Codespaces

No application dependencies or tests need to run on the office laptop.

```bash
bash scripts/start-data.sh
bash scripts/cloud-verify.sh
```

The verification script uses a new database ending in `_test`, Redis database 15 and separate app ports 8001/5174. It does not reset the demonstration database. It runs preprocessing/model/resume checks, MongoDB/Redis API and permission tests, the production frontend build, full browser journeys, the presentation walkthrough, and the new survey/missing-field evidence checks. It stops the servers it started. Test output/screenshots are in ignored `test-results/`.

For a fresh Codespace, install the browser-test tool there once:


```bash
.venv/bin/python -m pip install playwright==1.65.2
.venv/bin/python -m playwright install --with-deps chromium
```
## Coverage

- Original-column validation; CSV/Excel parity; missing labels excluded.
- Nulls, duplicate technology names, aliases, punctuation and invalid numeric values.
- Training-only vocabulary/median; duplicate input groups cannot cross splits.
- Saved model checksum/provenance, shared encoder and finite predictions.
- Empty and unseen profiles abstain; reciprocal explanations use actual intersections.
- Authentication, refresh/logout, ownership, project capacity, invites and feedback.
- Activities, individual organizers, joining/location filters and separate interests.
- Chat permission checks, WebSockets, attachment validation and privacy.
- Profile field mapping, actual metrics page, empty-profile UI and responsive layouts.

Constructed unit-test and browser fixtures are explicitly fictional. They are not fed into the model training script. Statistical tests are separate from application tests; a passing app test does not establish social recommendation quality.

The committed model is checked by the unit tests. To reproduce statistical training in the cloud:

```bash
.venv/bin/python -m pip install -r ml/requirements-training.txt
.venv/bin/python -m ml.train --download
```

CI independently downloads the checksum-pinned original data and trains offline. Its generated reports are workflow artifacts; it does not silently rewrite published README metrics.
