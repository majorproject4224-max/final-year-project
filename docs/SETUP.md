# Run connecT AI

Use a local or cloud development environment.

## Browser-only development

GitHub Codespaces runs Python, Node, MongoDB and Redis on a remote machine. Your browser is the editor and preview.

1. Open this repository on GitHub and select the `main` branch.
2. Choose **Code → Codespaces → Create codespace on main**.
3. The included dev container installs the project dependencies remotely. Wait for creation and the data-service startup to finish.
4. In the Codespaces terminal run:

```bash
bash scripts/start-data.sh
bash scripts/dev.sh
```

Open the forwarded **5173** port from the Ports panel. Keep it private. The React development proxy carries API and WebSocket traffic, so you do not need to expose MongoDB, Redis or port 8000.

If startup says Docker is unavailable, wait for the container to finish initialization and rerun `bash scripts/start-data.sh`. If setup was interrupted, rerun `bash scripts/bootstrap.sh`.

If Codespaces says **recovery mode due to a container error**, the normal environment has not been created. Pull the latest committed configuration with `git pull --ff-only`, then open the command palette (**Ctrl+Shift+P**) and select **Codespaces: Rebuild Container**. Wait for setup to complete before running the commands above. Rebuilding uses the existing Codespace. Do not run the application in the recovery container.

The dev-container Dockerfile removes an unused Yarn APT source from the Python base image, and the Node feature avoids adding it again. This project uses npm. This prevents stale Yarn signing keys from blocking Docker installation while preserving package-signature verification. [Node feature options](https://github.com/devcontainers/features/tree/main/src/node)

Forward **5173**, not **1573**. Adding a forwarded port does not start the application; `bash scripts/dev.sh` must still be running in the terminal.

The codespace has a free-use quota for personal accounts, covering compute and storage. Without a paid spending setup, access is restricted after quota exhaustion until renewal. Stop the codespace when finished; delete unused codespaces to release storage. Check your account's remaining allowance before creation. [GitHub's included-use documentation](https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage)

Codespaces configuration is supplied; its initial account provisioning must be performed in your GitHub account. The application itself is tested in GitHub Actions.

## Local Windows setup

For local development, install: Git, Python 3.12, Node.js 22 and Docker Desktop. Start Docker Desktop. Docker runs the development databases; Python and Node run the application.

Open PowerShell and clone:

```powershell
git clone https://github.com/majorproject4224-max/final-year-project.git
cd final-year-project
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm ci --prefix frontend
Copy-Item .env.example .env
```

Do not overwrite an existing `.env`. Its development defaults use a local database named `connect_ai`. The example secret is for local development only.

Start MongoDB and Redis:

```powershell
docker compose up -d --wait
docker compose exec mongo mongosh --quiet --eval 'try { rs.status() } catch (e) { rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]}) }'
```

Wait a few seconds, then initialize indexes:

```powershell
.\.venv\Scripts\python.exe backend/manage.py setup_db
```

If MongoDB reports it is not primary yet, wait briefly and repeat the index command. A replica set is required for transactions that prevent overfilled teams.

In **terminal 1**, from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn config.asgi:application --app-dir backend --host 127.0.0.1 --port 8000
```

In **terminal 2**, from the project root:

```powershell
npm run dev --prefix frontend
```

Open **http://localhost:5173**. Create an account and complete your profile. Use Ctrl+C to stop each server; `docker compose stop` stops the databases without deleting their volume.

Virtual-environment activation is optional; the explicit Python path above avoids PowerShell execution-policy changes.

### Linux / macOS

With Python 3.12, Node 22 and Docker available:

```bash
bash scripts/bootstrap.sh
bash scripts/start-data.sh
bash scripts/dev.sh
```

### Optional fictional presentation data

A new database is empty. Recommendations need other profiles/projects. Either create accounts through registration or add the clearly marked fictional presentation records. This command requires debug mode and a disposable `_test` database or the explicit `PRESENTATION_DATA_ENABLED=1` opt-in. The opt-in defaults to disabled.

In PowerShell, enter a private password without printing it:

```powershell
$env:PRESENTATION_PASSWORD = Read-Host 'Choose a password for fictional presentation accounts' -MaskInput
$env:PRESENTATION_DATA_ENABLED = '1'
.\.venv\Scripts\python.exe backend/manage.py prepare_presentation --apply --password-env PRESENTATION_PASSWORD
Remove-Item Env:PRESENTATION_PASSWORD
Remove-Item Env:PRESENTATION_DATA_ENABLED
```

`-MaskInput` requires PowerShell 7. In Windows PowerShell 5.1, set `PRESENTATION_PASSWORD` in your uncommitted `.env` instead, run the command, then remove that line.

In Codespaces/Linux:

```bash
read -rs -p "Choose a presentation password: " PRESENTATION_PASSWORD
export PRESENTATION_PASSWORD
PRESENTATION_DATA_ENABLED=1 .venv/bin/python backend/manage.py prepare_presentation --apply --password-env PRESENTATION_PASSWORD
unset PRESENTATION_PASSWORD
```

Use at least 8 characters and avoid common passwords. The five fictional Indian-name accounts and five projects are listed in [PRESENTATION.md](PRESENTATION.md). Re-running does not overwrite existing profiles or passwords. Do not seed these accounts into a public production database.

### Local setup without Docker

Use an Atlas free database as described in the deployment guide. Put its connection string in your local `.env`, allow your personal IP, and run `setup_db`. For a single-process local session you can leave `REDIS_URL=` empty with `DJANGO_DEBUG=1`; Channels then uses an in-memory layer. Deployed chat requires Redis-compatible shared storage.

### Model and dependency files

`backend/requirements.txt` pins application packages and works across operating systems. `backend/requirements-lock.txt` records the full **Linux/Python 3.12** cloud environment for Render. Do not install that Linux lock file directly on Windows (`uvloop` is Unix-only).

The checked-in `ml/models/survey-recommender.joblib` is ready for inference. Regeneration is optional:

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/requirements-training.txt
.\.venv\Scripts\python.exe -m ml.train --download
```

Keep model and scikit-learn versions aligned. Training with another version requires rebuilding the artifact and rerunning checks.

## Common problems

| Symptom | What to check |
|---|---|
| Database unavailable | Docker/Atlas is running, URI is correct, Atlas access list includes your IP |
| Transactions require a replica set | Run the replica-set initialization above; a standalone MongoDB is insufficient |
| Recommendations empty | Complete profile; create/seed other students and open projects; unknown technologies may be outside the survey training vocabulary |
| Recommendations temporarily unavailable | Model bundle exists and scikit-learn matches its metadata |
| Chat unavailable | Connection must be accepted; Redis must run if configured; use port 5173 |
| Site cannot contact backend | Start both terminals; remove production frontend env values while using the local proxy |
| Frontend refuses host in Codespaces | Rebuild the dev container with this repository's Vite configuration |
| Old prototype data fails indexes | Use a fresh development database; preserve the old database and review any duplicates before migration |
