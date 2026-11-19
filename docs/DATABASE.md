# Browse the ConnectAI database

The application database is **`connect_ai`**. MongoDB calls a table-like group a **collection** and an individual record a **document**. Application collections include `users`, `profiles`, `projects`, `connections`, `conversations`, `messages`, `events`, `applications` and `invitations`.

## Open the visual browser in Codespaces

1. Press **Ctrl + Shift + P**, select **View: Show MongoDB**.
2. Expand **Connections → 127.0.0.1:27017 → connect_ai**.
3. Expand a collection and click **Documents**. This opens the visual record browser; writing a query is not required.
4. Use **Refresh** after changing data through the website.

If a connection has not been saved, use **MongoDB: Connect with Connection String** and enter `mongodb://127.0.0.1:27017/?replicaSet=rs0&directConnection=true`. Install the official `mongodb.mongodb-vscode` extension in the Codespace. It is included in the development-container extension configuration.

`users` stores accounts. `profiles` stores technology answers and community preferences, linked by `user_id`. A user's `_id` remains the same across a database rename, so relationships and login credentials are preserved. The five fictional presentation accounts are separate from the original survey used for ML training.

The `admin`, `config` and `local` databases belong to MongoDB. Databases ending in `_test` contain isolated test records; they are not the application's active database.

## Rename an older local application database

Changing only `.env` does not move existing records. The maintenance tool reads the current database name from `.env`, previews collection counts, creates a private native MongoDB backup, moves collections without overwriting another database, and verifies complete BSON contents and index definitions. It updates `.env` only after verification. A failed move rolls back the moved collections. The application must remain stopped throughout this procedure; do not edit records from the database extension during it.

```bash
# Preview while the current application is available:
.venv/bin/python scripts/rename_database.py --target connect_ai
# Stop scripts/dev.sh with Ctrl+C, then apply:
.venv/bin/python scripts/rename_database.py --target connect_ai --apply
# Start the application using the verified new database:
bash scripts/dev.sh
```

MongoDB and Redis remain running. The tool accepts the project's local Docker deployment only. It refuses a nonempty destination and never overwrites its records. A verified empty source namespace is removed after all its collections have moved. The backup, old environment file and verification receipt stay under ignored `.presentation-private/database-rename-*` folders. Refresh the Connections view after completion.

The native backup uses [`mongodump`](https://www.mongodb.com/docs/database-tools/mongodump/); collection moves use MongoDB's [`renameCollection`](https://www.mongodb.com/docs/manual/reference/command/renamecollection/) command. [`mongorestore`](https://www.mongodb.com/docs/database-tools/mongorestore/) can recover the compressed archive. Never commit the private backup or environment file.

## Verified Codespace maintenance - 19 November 2026

- All 30 backend checks passed in 27.094 seconds against the original MongoDB storage.
- The database rename verified complete BSON contents, record IDs and indexes across all 14 application collections.
- Six accounts, five profiles, five projects, two events, the existing connection, conversation and message were preserved. Password hashes were unchanged.
- A private compressed database backup and verification receipt were retained. The active database is `connect_ai`.

The Codespace container initially had an open-file limit of 1,024 and logged `Too many open files`. The MongoDB service in `docker-compose.yml` now sets both soft and hard `nofile` limits to 64,000, following [MongoDB resource-limit guidance](https://www.mongodb.com/docs/v8.0/reference/ulimit/). This setting applies only to that Docker container. The original database volume is retained; no hardware-security workaround is enabled.
