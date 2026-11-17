# API reference

Base: `/api`. Requests/responses are JSON, except Resume/chat uploads and attachment downloads. Add `Authorization: Bearer <access>` to protected requests. IDs are MongoDB ObjectId strings; timestamps are ISO 8601 UTC. The client formats local dates.

Lists generally return `{items, page, page_size, total}`. Page size defaults to 20 and is capped at 50. Recommendations, conversations and saved targets return bounded `items` lists. Errors use `detail` and `code`, or field validation errors. Codes include 400 validation, 401 authentication, 403 permission, 404 absent/inaccessible, 409 conflict, 429 rate limit and 503 unavailable dependency.

## Accounts and profiles

| Method | Endpoint | Payload / result |
|---|---|---|
| POST | auth/register/ | name, email, password → user + tokens |
| POST | auth/login/ | email, password → user + tokens |
| POST | auth/token/refresh/ | refresh → new access AND refresh; replace both |
| POST | auth/logout/ | Revokes current session |
| GET | auth/me/ | Current user ID/name/email |
| PATCH | auth/me/ | current_password, new_password; revokes all sessions |
| GET / PUT | profiles/me/ | Own profile; PUT validates a complete profile |
| POST | profiles/resume-suggestions/ | multipart field resume, PDF/DOCX ≤5 MB; suggestions only |
| GET | students/ | q, domain, page, page_size |
| GET | students/{user_id}/ | Public profile and viewer's connection status |

Profile PUT fields: name, branch, academic_year (1–4), skills (array), interests (array), domain, experience, preferred_project_type, projects_completed, availability_hours (1–40), bio, city, phone, github URL, share_contact. Skills/interests are normalized. Phone is hidden unless the viewer owns the profile or is an accepted connection and sharing is enabled. Email/password/session data is not returned by student endpoints.

## Connections

| Method | Endpoint | Payload |
|---|---|---|
| GET / POST | connections/ | POST: user_id; GET includes status and sent/received direction |
| PATCH | connections/{id}/ | action: accept or reject; recipient only |
| DELETE | connections/{id}/ | Cancel/remove as either participant |

## Projects and teams

| Method | Endpoint | Payload |
|---|---|---|
| GET | projects/ | q, status (default Open), mine=1, pagination |
| POST | projects/ | Project fields below |
| GET / PATCH | projects/{id}/ | Detail / owner edits or status change |
| GET | projects/{id}/applications/ | Owner-only paginated applicants |
| POST | projects/{id}/applications/ | Empty object, apply as current user |
| PATCH | projects/{id}/applications/ | application_id, decision: Accepted/Rejected; owner only |
| DELETE | projects/{id}/applications/ | Withdraw own pending application |
| DELETE | projects/{id}/members/{user_id}/ | Owner removes member or member leaves; owner cannot leave |
| GET / POST | invitations/ | POST: project_id, recipient_id; owner only |
| PATCH | invitations/{id}/ | decision: Accepted/Rejected; recipient only |
| DELETE | invitations/{id}/ | Sender cancels pending invitation |

Project fields: title, description, required_skills, required_interests, domain, project_type, team_size (2–10 including owner), required_experience, expected_hours and optional deadline. Detail includes members, is_member and application_status.

PATCH status transitions are Open → In Progress/Cancelled, In Progress → Open/Completed/Cancelled. Ended projects are preserved. Joining requires Open and capacity; membership and decision are transactional.

## Recommendations and feedback

| Method | Endpoint | Meaning |
|---|---|---|
| GET | recommendations/users/ | Up to 12 new potential connections |
| GET | recommendations/projects/ | Up to 12 recruiting projects |
| GET | projects/{id}/teammates/ | Owner-only project-specific student ranking |
| GET | recommendations/teammates/{project_id}/ | Alias for teammate ranking |
| POST | interactions/ | target_type student/project, target_id, action view/save/ignore/unsave |
| GET | interactions/ | Up to 100 saved targets |
| POST | feedback/ | project_id, to_user_id, rating 1–5, comment; shared completed project required |

Recommendation items contain compatibility_score and explanations. Only scores meeting the classifier’s 50% decision threshold are returned; this threshold is a product filter, not a claim of calibrated probability. The response includes model_notice when a model was used. Empty results contain a detail explaining missing information or candidates. Scores from the current synthetic model are labeled accordingly. Saving/ignoring does not retrain anything.

## Events

| Method | Endpoint | Meaning |
|---|---|---|
| GET / POST | events/ | Upcoming list / title, description, location, starts_at |
| DELETE | events/{id}/ | Organizer only |
| POST / DELETE | events/{id}/attendance/ | Attend / leave |

## Messaging

| Method | Endpoint | Meaning |
|---|---|---|
| GET / POST | conversations/ | List / recipient_id; requires accepted connection |
| GET | conversations/{id}/messages/ | Latest 50; before or after ObjectId cursor, never both |
| POST | conversations/{id}/messages/ | JSON or multipart: content (≤4000 chars), client_id (UUID), optional repeated attachments fields; duplicate-safe |
| GET | conversations/{id}/messages/{message_id}/attachments/{attachment_id}/ | Authenticated binary download; both conversation membership and accepted connection required |
| PATCH | conversations/{id}/messages/ | through: latest visible message ID; read receipt |
| POST | conversations/{id}/websocket-ticket/ | One-use ticket, expires in 60 seconds |

Connect to `/ws/conversations/{id}/?ticket=...` with an allowed Origin. Receive:
- `{type:"message", message:{id, sender_id, content, created_at, read_by, ...}}`
- `{type:"read", reader_id, through}`

Optional WebSocket send: `{content, client_id}`, acknowledged with `{type:"sent", message_id}`. Persistent content is still written through the same service. Invalid/auth-revoked connections cannot receive further chat events.

Attachment uploads use multipart REST, not WebSocket frames. A message must contain text or a file. Up to 3 files, 5 MiB per file, 10 MiB total. Supported extensions: JPG/JPEG, PNG, WebP, PDF, DOCX, XLSX, PPTX, TXT, CSV and ZIP. Text/CSV must be UTF-8. Images must be still images of at most 12 million pixels; the server decodes/re-encodes them, validates the format and removes metadata. Other files are download-only with basic format checks; this is not malware scanning.

Messages/history/live events include an `attachments` array of `{id, name, content_type, size, is_image, width?, height?}`. Binary data is excluded from queries for history and never serialized into events. The client fetches private downloads with its usual Authorization header and creates temporary browser object URLs for image previews. Access tokens are never included in attachment URLs. Downloads return `Content-Disposition: attachment`, `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff` and a restrictive CSP.

Files are embedded as BSON binary in their message, below MongoDB's 16 MiB document limit. The app has a shared 100 MiB attachment budget by default (`CHAT_ATTACHMENT_STORAGE_MB`). A MongoDB transaction commits the message and storage counter together. Retrying the same conversation/sender/client UUID does not create a second message or consume the budget twice. Failed validation/budget checks save no message. Text messages remain available when attachment storage is full. There is no attachment-deletion interface yet; use dedicated object storage and a retention policy before expanding beyond a small demo.

## Operations

`GET /api/health/` is a lightweight process check. `GET /api/health/ready/` checks MongoDB connectivity. Neither endpoint exposes credentials. Readiness does not certify recommendation quality or Redis health.
