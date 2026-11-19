# ConnectAI

**AI/ML-Based Social Connection Recommendation Platform**

[![Project checks](https://github.com/majorproject4224-max/final-year-project/actions/workflows/ci.yml/badge.svg)](https://github.com/majorproject4224-max/final-year-project/actions/workflows/ci.yml)

ConnectAI helps people discover potential collaborators, build project teams and take part in community activities. It brings profiles, skills, interests, connection requests, projects, private messaging and personalized suggestions into one platform.

The platform is open to **students, developers, individuals, clubs, NGOs and other community organizations**. Anyone with an account can organize an activity, including a volunteer drive, workshop or meetup. Academic details and an organization name are optional; people can create an interest-based profile without technical skills.

Developed as a **B.Tech CSE major project**, ConnectAI combines a working collaboration platform with an explainable, reproducible machine-learning pipeline. The current ML models focus on technical profiles and projects. Community activity suggestions use a separate interest-matching method.

**The bundled ML datasets and presentation accounts are fictional.** Match percentages are model estimates learned from documented synthetic labels, not validated probabilities of successful real collaboration. Training spreadsheets are separate from the live application database.

## What you can do

1. **Create your profile:** add interests, optional skills, availability and a city. Academic information is optional.
2. **Find and connect with people:** browse profiles, review recommendations and send connection requests.
3. **Build a project team:** publish a project, apply to join, invite collaborators and manage membership and project status.
4. **Communicate:** chat with accepted connections and share private images and documents.
5. **Organize or join an activity:** publish a drive, workshop, meetup, sports or cultural activity and discover opportunities related to your interests.

For example, an individual can organize a tree-plantation drive and tag it with **Gardening** and **Environmental conservation**. People who select those interests can see it in **Activities for you**, review why it was suggested and join. The same workflow supports food-distribution drives, photography meetups and coding workshops. See the [community activity guide](docs/ACTIVITIES.md).

## Start here

- **Presentation:** [Five fictional Indian-name accounts, projects and a demonstration walkthrough](docs/PRESENTATION.md).
- **Office laptop / no local installations:** [Use GitHub Codespaces in your browser](docs/SETUP.md#browser-only-development).
- **Personal laptop:** [Windows setup and run instructions](docs/SETUP.md#personal-windows-laptop).
- **Community activities:** [Individual organizers, interest matching and joining activities](docs/ACTIVITIES.md).
- **Deployment plan:** [Vercel + Render + MongoDB Atlas guide](docs/DEPLOYMENT.md). Provider choices, database setup and current free-tier limits must be reviewed with the owner before deployment.
- **Understand the code:** [Architecture](docs/ARCHITECTURE.md), [API reference](docs/API.md), [beginner learning guide](docs/LEARNING.md).
- **College report / viva:** [Project report](docs/PROJECT_REPORT.md), [ML methodology](docs/ML_METHODOLOGY.md), [measured results](docs/RESULTS.md), [demonstration script](docs/DEMO.md).

### Run in an existing Codespace

After the included development environment has finished setting up, run these commands from the repository root:

```bash
bash scripts/start-data.sh
bash scripts/dev.sh
```

Open forwarded port **5173** from the **Ports** panel. The first command starts MongoDB and Redis; the second starts the application. Keep the Codespace running while using the preview. For first-time setup or troubleshooting, follow [SETUP.md](docs/SETUP.md).

## Preview

These screenshots show fictional records from an earlier automated test run; the current theme and interface labels may differ.

![Dashboard with fictional test records](docs/screenshots/dashboard-desktop.png)

[Mobile view](docs/screenshots/dashboard-mobile.png) · [Project team](docs/screenshots/project-team.png) · [Live chat](docs/screenshots/chat-desktop.png)

## Implemented workflows

| Area | Functionality |
|---|---|
| Accounts | Registration, login, rotating JWT refresh, logout, password changes and session revocation |
| Profiles | Normalized skills/interests, optional academic and organization details, availability, city preferences, contact privacy and optional PDF/DOCX resume suggestions |
| Connections | People search, profile details, connection requests, acceptance/removal |
| Projects | Create/edit, apply/withdraw, owner decisions, invitations, capacity-safe team formation, progress and completed-project feedback |
| Discovery | User → user, user → project and project → teammate recommendations for technical profiles/projects, with actual feature comparisons |
| Events & activities | Individuals, clubs and organizations can publish drives, workshops and meetups; interest-based dashboard suggestions, city preferences, capacity-safe joining, editing and private participant lists |
| Messaging | One-to-one chat, private image/file attachments, previews/downloads, persistent history, read receipts, WebSocket delivery, reconnect and duplicate-safe sending |
| Personal space | My teams/projects, sent/received invitations and saved projects |

After forming a team, members can discuss responsibilities, exchange files and update the overall project status. They can use a shared GitHub repository for code, issues and reviews. ConnectAI does not currently include a code editor or a task board.

## Recommendation methods

| Recommendation | Method | What the user sees |
|---|---|---|
| People with compatible technical profiles | K-Means candidate discovery followed by a user–user Random Forest classifier | Ranked suggestions, model scores and actual shared skills/interests |
| Projects suited to a user | K-Means candidate discovery followed by a user–project Random Forest classifier | Project suggestions with requirement comparisons |
| Teammates for a project | The user–project classifier compares candidates with the actual project requirements | Owner-only suggestions with skill coverage and other comparison reasons |
| Community activities | Shared normalized interest tags and optional city/online preferences | Reasons based on shared interests and location, without an ML percentage |

Activity suggestions exclude an organizer's own activities, activities already joined, full activities and past activities. An organization name is self-described, not a verification badge. The existing technical ML models are not used to predict volunteer suitability. An activity-specific model would require suitable data, defensible labels and its own evaluation.

New users can receive profile-based suggestions without interaction history. Missing profile information or unsupported vocabulary produces guidance to improve the profile or browse manually. The system does not invent match scores when models or useful information are unavailable.

## Machine learning

- **K-Means:** TF-IDF features from normalized skills/interests; select k by silhouette over 2–10, retain inertia for analysis.
- **Random Forest:** separate user–user and user–project classifiers, trained on synthetic technical-profile/project comparisons.
- **Evaluation:** entities are separated between training/test sets; supervised features are recomputed from raw profiles. Reports include majority and similarity baselines, confusion matrices and ranking metrics.
- **Artifacts:** the repository includes the offline trained bundle, Excel/CSV data and measured results. Inference loads the bundle once per process; request handlers do not train.

The development dataset contains **420 fictional profiles, 84 project scenarios, 6,000 user pairs and 6,000 user–project pairs**. Labels come from a documented compatibility rubric. Evaluation measures how well the models reproduce that rubric; it does not establish real-world teamwork success. See [dataset design and methodology](docs/ML_METHODOLOGY.md) and [actual evaluation results](docs/RESULTS.md).

No external AI API subscription is needed. There is no automatic online retraining, and activity matching works independently of the saved ML models.

## Technology stack

| Layer | Technology and purpose |
|---|---|
| Frontend | React, JavaScript, Vite, React Router, Axios and responsive CSS |
| Backend | Python, Django REST Framework and domain services |
| Database | MongoDB; explicit PyMongo domain operations with the matching official Django MongoDB backend configured for Django integration |
| Authentication | JWT access/refresh tokens, Django password hashing and revocable sessions |
| Live messaging | Django Channels, WebSockets and Redis for transient events; MongoDB for message history |
| Machine learning | Pandas, NumPy, scikit-learn and Joblib; Excel and CSV input |
| Development and checks | GitHub Codespaces, Docker data services and GitHub Actions |

The API, live chat and recommendation inference share one Django/ASGI backend. Training runs separately and saves artifacts for inference. See [architecture and database decisions](docs/ARCHITECTURE.md).

## Repository structure

```text
backend/       Django API, Channels, permissions and domain services
frontend/      React pages, reusable components and API client
ml/            Shared preprocessing, offline training, saved model and metrics
dataset/       Reproducible generator + explicitly synthetic Excel/CSV datasets
docs/          Setup, architecture, API, methodology, results and report
scripts/       Development and deployment startup helpers
tests/         ML, resume and browser journey tests
.devcontainer/ Browser-only development configuration
```

## Checks

GitHub Actions trains from the reproducible generator, checks Django, tests against a disposable MongoDB replica set and Redis, builds React, and runs a real Chromium browser journey. Test artifacts include screenshots, a browser trace, the trained model and measured metrics. See [testing instructions](docs/TESTING.md).

Do not run the database tests on an important database: they deliberately reset the database and refuse names that do not end in `_test`.

## Scope and limitations

This is an academic prototype for social connections, project collaboration and community participation. The interface supports a broader community, while the current ML training data remains focused on technical profiles and projects.

There is no email verification/recovery, moderation console, organization verification, profile photo storage, group chat or presence indicator. Profiles use initials as avatars. Candidate retrieval and attachment storage are bounded for a small demonstration. Synthetic labels and related project scenarios limit what evaluation proves. Read [the ML limitations](docs/ML_METHODOLOGY.md#limitations) and [activity limitations](docs/ACTIVITIES.md#implementation-and-limits) before presenting results.

## Next steps

- Review the hosting and database choices with the owner, confirm the available free tiers and deploy the frontend and backend.
- Check the deployed connection, project, activity and messaging workflows; fix issues found on desktop and mobile.
- Collect user feedback and, with consent, real collaboration outcomes for later offline model evaluation and improvement.

The deployment guide describes proposed services; this repository does not establish that a public deployment is live or create hosting resources. Free-tier limits and availability must be checked before provisioning.

## Conceptual reference

The conceptual reference is [RohitGaira/connecT-University-Social-Platform](https://github.com/RohitGaira/connecT-University-Social-Platform). This implementation uses its own React/Django/MongoDB/ML architecture. Earlier Flask, SQLite and static-site experiments were removed from the current tree to leave one supported application; they remain in Git history at `8eaf15a`.
