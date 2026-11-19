# Presentation accounts and demonstration

These five Indian-name profiles are fictional, curated presentation fixtures. They are not real people or new ML training/evaluation data. The preparation command checks the real-survey discovery pipeline. The score combines observed technology overlaps with predicted language preferences; it is not a probability of successful collaboration.

| Account | Sign-in email | Demonstration role |
|---|---|---|
| Aarav Sharma | aarav@connect.example | Start here: AI projects, a new people recommendation and a connected chat |
| Priya Verma | priya@connect.example | Already connected to Aarav; owns StudyCircle AI |
| Rohan Mehta | rohan@connect.example | Compatible unconnected profile, available for the connect/accept demonstration |
| Ananya Iyer | ananya@connect.example | Frontend collaborator and plantation-drive organizer |
| Kabir Singh | kabir@connect.example | Backend collaborator and an individual ration-drive organizer |

Five presentation projects: StudyCircle AI, Resume Insights, Open Data Explorer, Green Together and FoodShare Connect. Two fictional community activities demonstrate shared-interest matching. Profiles and descriptions identify the records as presentation examples.

## Prepare in Codespaces or on a personal laptop

First stop the application server. MongoDB and Redis must remain running. Commands below run from the repository root and require the development database name to end in `_demo` or `_test`, with `DJANGO_DEBUG=1`.

```bash
# Read-only preview, including genuine saved-model predictions:
.venv/bin/python backend/manage.py prepare_presentation
# Apply after reviewing the preview:
.venv/bin/python backend/manage.py prepare_presentation --apply --replace-legacy-demo
bash scripts/dev.sh
```

The command creates a random shared password for new presentation accounts and stores it in a private file under `.presentation-private/`. It prints the file's path, never the password. Read that file privately for the sign-in details. An optional `PRESENTATION_PASSWORD` environment variable supplies a chosen password; it must pass Django validation. Credentials/backups are ignored by Git. The former `seed_demo` command is retired.

Re-running preserves existing presentation passwords, profiles, projects and registrations. It does not reset the demonstration after you connect to Rohan. Existing presentation account credentials are not replaced with a newly generated password. Accounts with conflicting email addresses or unrelated records with a fixture ID cause the command to stop before database changes.

## What is replaced

Only accounts with `data_source=synthetic_demo` AND a `demo<number>@example.invalid` email are selected. Their profiles, projects, organized events, connections, conversations/messages and associated interactions/sessions are removed. Their membership/attendance references are removed from other people's projects/events. A private compressed BSON-JSON snapshot of affected records is saved before the transactional change, including attachment bytes and storage accounting. Attachment storage used by removed messages is released. Manually created accounts and the projects/activities they own are preserved. No database is dropped and the offline ML datasets/models are untouched.

## Five-minute presentation

1. Sign in as Aarav. Show Rohan under Recommended for you, open the genuine feature explanations, and switch to Projects to show StudyCircle AI.
2. Explain that Aarav and Priya are already connected, so Priya is under Connections rather than new recommendations. Open Messages and exchange a live message with Priya in another browser/device. No fabricated conversation is seeded.
3. Connect to Rohan; accept the request as Rohan in another session. Return to Aarav's Connections and open the new chat. Existing connections intentionally disappear from new recommendations.
4. Show a project, apply as an interested account, and accept from its owner's session. Project membership and capacity use the existing workflow.
5. Show Activities for you. Aarav's sustainability interest matches Ananya's plantation drive. Rohan's community-service interest matches Kabir's ration drive. These are explicit interest matches, not ML percentages. Join and show the organizer's participant list.

Use separate browsers or browser profiles for simultaneous accounts. These are development-only fixtures; do not put their shared credentials into a public production deployment. The trained model predicts recorded language preferences from the real Stack Overflow 2024 survey. Fictional accounts are UI fixtures only and never enter model training. See [TEACHER_DEMO.md](TEACHER_DEMO.md).
