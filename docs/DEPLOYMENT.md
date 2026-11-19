# Free deployment plan — approval required

No hosting resources have been created. Confirm the provider choices with the project owner before carrying out this guide. Prices and account eligibility can change; verify the dashboard says **Free / ₹0** at creation.

## Proposed services

| Part | Provider and plan | Purpose |
|---|---|---|
| React | Vercel Hobby | Static frontend |
| Django + Channels | Render Free web service | REST API and WebSockets, one process |
| Persistent database | MongoDB Atlas Free | Users, projects, messages, sessions |
| Shared messaging/cache | Render Free Key Value | Redis-compatible Channels groups and throttling |

Vercel's Hobby plan is free with monthly limits; exceeding limits can suspend features. Review the plan's terms for your academic, non-commercial use. [Vercel Hobby](https://vercel.com/docs/plans/hobby)

Render's free web service sleeps after 15 idle minutes and can take about a minute to wake. The workspace gets 750 free instance-hours monthly. Its filesystem is temporary. Free Key Value can lose its contents on restart; our permanent messages and sessions are in MongoDB. With a payment method, some bandwidth/build overages can incur charges; without one, services/builds can instead be suspended. Keep paid upgrades off and review spend controls before deployment. [Render free services](https://render.com/docs/free)

Atlas provides a Free cluster with resource and regional limits; it is a replicated deployment suitable for this project's transactions. Select **Free**, not a paid trial or dedicated cluster. [Atlas Free limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)

**PythonAnywhere Free is unsuitable for this MongoDB requirement.** PythonAnywhere says external MongoDB connectivity needs a paid account. [PythonAnywhere MongoDB documentation](https://help.pythonanywhere.com/pages/MongoDB/)

This setup is intended for a small presentation. Free hosting is not a promise of unlimited capacity or permanent uptime.

## 1. MongoDB Atlas

After owner approval:

1. Create a Free cluster in a region reasonably near the backend.
2. Create a separate database user with read/write access only to `connect_ai`. Use a generated password.
3. Copy its driver connection string into Render's secret environment field as `MONGODB_URI`. Never paste credentials into code, issues or chat.
4. In Atlas Network Access, allow Render's published outbound IP ranges for your service. Add your personal IP separately only if you need local access. Avoid a blanket public allow rule.
5. Do not import training spreadsheets as real student records. The ML dataset and live user database are separate.

## 2. Render API and Key Value

The root `render.yaml` is a prepared Blueprint. It explicitly uses free plans and disables automatic deploys. Import it only after approving the services. Keep the API and Key Value in the same region.

The backend must use the **repository root** as its root directory because it imports `ml/`.

| Setting | Value |
|---|---|
| Runtime | Python 3.12.16 |
| Build | `pip install -r backend/requirements-lock.txt` |
| Start | `bash scripts/render-start.sh` |
| Health path | `/api/health/` |
| Plan | Free |
| Workers | 1 |

The start script creates indexes, then starts Uvicorn as an ASGI server. It does not train models. Never use the old Flask/Gunicorn startup command.

Required environment:

```text
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<random secret of at least 50 characters>
MONGODB_URI=<private Atlas connection string>
MONGODB_DATABASE=connect_ai
REDIS_URL=<Render Key Value internal connection string>
FRONTEND_URL=https://YOUR-FRONTEND.vercel.app/
CORS_ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
```

The Blueprint links Redis and prompts for your secret. Generate it privately with Python’s secrets.token_urlsafe(64) on your personal laptop or in Codespaces; paste only into Render’s secret field. The Render hostname is automatically included in Django's allowed hosts. Put exact frontend origins in CORS, with no trailing slash. Do not use wildcard origins. Leave HTTPS redirects enabled.

Key Value should have `noeviction` and private access. Its contents are disposable; losing them may interrupt live delivery and reset rate counters. Clients reconnect and retrieve permanent history from MongoDB.

## 3. Vercel React

Import the same GitHub repository:

| Setting | Value |
|---|---|
| Framework | Vite |
| Root directory | `frontend` |
| Install | `npm ci` |
| Build | `npm run build` |
| Output | `dist` |
| Plan | Hobby |

Add these **public** build variables:

```text
VITE_API_URL=https://YOUR-BACKEND.onrender.com/api
VITE_WS_URL=wss://YOUR-BACKEND.onrender.com
```

Vite embeds these in the browser bundle. Never put MongoDB credentials, Redis credentials or the Django secret into any `VITE_` variable. Redeploy the frontend after changing them.

`frontend/vercel.json` handles React route refreshes. Once Vercel assigns the final domain, update Render's frontend/CORS values to match. Preview domains need explicit authorization before they can call the backend.

## 4. Verify the deployed result

- API health responds and readiness confirms MongoDB.
- Register two accounts and complete different profiles.
- Create a project, apply from the other account and accept it.
- Accept a connection and chat from two browsers, checking live delivery and history after reload.
- Check people discovery, project skill coverage, reciprocal explanations, empty profiles and the real-data model notice.
- Check the mobile layout and direct route refresh.
- Check service memory and usage during this small installation. No production load test has been performed.

The app stores no permanent uploads on Render disk. Resumes are parsed for suggestions; the user explicitly saves reviewed profile fields. Chat images/documents are stored as bounded binary attachments in MongoDB, with authenticated downloads and a default 100 MiB total attachment budget (`CHAT_ATTACHMENT_STORAGE_MB`). This consumes database capacity; the budget is not a replacement for monitoring the provider's total storage limit. No paid file-storage service is required. A future larger deployment needs object storage, malware scanning and a retention policy. The trained bundle is part of the deployed Git checkout.

If a provider asks for a paid resource or the app exceeds a free limit, stop and discuss it with the owner. Do not silently upgrade.
