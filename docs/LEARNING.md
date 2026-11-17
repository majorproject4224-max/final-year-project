# Learn enough to explain your project

You already know Django REST Framework. Start there, then connect the new pieces to it.

## MongoDB is more than changed SQL syntax

MySQL stores rows in related tables with a relational schema. MongoDB stores BSON documents in collections, which may contain arrays and embedded values. Both support indexes, validation and transactions, but the data-modeling and query choices differ.

In this app, a project document has a small array of member IDs. Messages live in a separate collection because history grows indefinitely. A transaction joins a student and updates the application together. A unique index prevents duplicate requests.

Learn these operations in `platform_api/mongo.py`, `people.py` and `services/projects.py`:

| Familiar idea | MongoDB equivalent in this project |
|---|---|
| Table / row | Collection / document |
| Primary key | `_id`, an ObjectId |
| INSERT | `insert_one` |
| SELECT | `find_one` / `find` |
| UPDATE | `update_one` with `$set`, `$addToSet`, `$pull` |
| Unique constraint | `create_index(..., unique=True)` |
| Transaction | PyMongo session with `with_transaction` |

Do not assume every relational join or Django ORM feature behaves the same. Read the short decision in [architecture](ARCHITECTURE.md).

## WebSockets, Channels and Redis

You need working basics, not expert-level distributed-systems knowledge.

| Component | Simple responsibility | What you should understand |
|---|---|---|
| DRF / HTTP | Receive requests such as “save this message” or “load history” | Authentication, serializers, permissions, responses |
| WebSocket | Keep a browser-to-server connection open for live events | Connect, receive, disconnect, reconnect |
| Django Channels | Route and handle those connections in Django | Consumer methods and conversation groups |
| Redis channel layer | Relay transient events between connections/processes | Group send, temporary delivery, shared service |
| MongoDB | Remember messages after restart | Persist before broadcasting; reload missed history |
| ASGI / Uvicorn | Run the Django HTTP + WebSocket app | Why an ASGI server is used |

A useful trace:

```text
Maya sends a message
→ authenticated DRF endpoint validates it
→ MongoDB stores it once using a client UUID
→ Channels publishes to the conversation group through Redis
→ Dev's WebSocket receives the event
→ React displays the message
```

If Dev reconnects later, MongoDB supplies history. Redis is not the permanent message database. The in-memory Channels layer is adequate for one local debug process but does not share messages across multiple processes. The deployed configuration uses Redis.

Read `persist_message`, `WebSocketTicketView`, `ConversationConsumer.connect` and `chat_message` in that order. Then read `ChatPage.jsx`.

## How this relates to LLD

Focus on concrete responsibilities and invariants rather than adding design-pattern classes everywhere.

- A serializer owns input shape and simple validation.
- A permission check establishes who may perform the action.
- The membership service owns “do not exceed team size” and “owner approves applications”.
- The recommendation service owns inference and candidate ranking.
- The frontend page owns a user workflow, while shared components own recurring controls.
- The database owns uniqueness and atomic writes where races matter.

A thin view delegates complex behavior to a focused service. A service can be a Python function; it does not need an abstract factory or a large inheritance hierarchy.

## Machine learning basics to explain

1. **Features:** measured similarities from normalized profiles.
2. **Label:** the target 0/1 judgment, with an explicit source.
3. **K-Means:** finds similar profile vectors without compatibility labels.
4. **Random Forest:** learns feature/label patterns to rank pairs.
5. **Train/test split:** hold out people, not just individual pair rows.
6. **Leakage:** the test set must not secretly influence classifier training.
7. **Evaluation:** compare to simple baselines and examine false positives/negatives.
8. **Limitations:** synthetic data proves the pipeline works, not that real teams succeed.

For the viva, explain a single prediction using actual shared/missing skills, then show where its feature values came from. Do not say the model “knows” whether two people will work well together.

## Suggested reading order

`README.md` → `docs/ARCHITECTURE.md` → serializers → account/profile endpoints → membership service → `ml/features.py` → `ml/train.py` → recommendation service → messaging → React pages.

Learn and demonstrate one vertical slice at a time: screen → API → validation → database/service → response. That is enough to understand the project progressively without learning every library at once.
