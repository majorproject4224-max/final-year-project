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

Profile PUT merges with the existing document and validates name, languages, databases, frameworks, platforms, wanted_languages (normalized lists, null becomes empty), and years_code (finite 0–51, nullable). The source mapping is in the dataset card. Names are not ML inputs. GET profiles/options/ returns technology vocabulary learned from training data.

Community settings are separate: community_interests, bio, city, phone, github URL, share_contact, organization_name and activity_location_preference (any/local). Local preference requires a city. Phone is visible only to its owner or an accepted connection when sharing is enabled. Student endpoints never return email/password/session data. Legacy academic fields are not model inputs or active profile controls.
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

Recommendation items contain match_score, score_label and explanations from actual comparisons. People scores combine explicit reciprocal learning overlaps, shared technologies and survey-trained preference affinity. The classifier predicts desired-language labels, not compatibility. K-Means supplies nearby groups; observed comparisons can cross groups. Empty/unsupported profiles abstain with a detail message. Existing connections and ignored targets are excluded. Candidate retrieval is capped at 2,000 profiles.

Project/teammate scores are observed requirement coverage, not supervised success predictions. The response model_notice describes the relevant scope. GET recommendations/evidence/ returns the published experiment's measured metrics, parameters, missingness results and limitations. Saving/ignoring never retrains models.
## Events and community activities

| Method | Endpoint | Meaning |
|---|---|---|
| GET / POST | events/ | Upcoming list / create as any signed-in user, no organization required |
| GET / PATCH / DELETE | events/{id}/ | Details / organizer edit / organizer deletion |
| POST / DELETE | events/{id}/attendance/ | Join with atomic capacity check / leave |
| GET | events/{id}/participants/ | Organizer-only paginated names and IDs; no email/contact details |
| GET | recommendations/activities/ | Up to six interest-matched activities, reasons, matching_method; no ML probability |

Activity fields: title, description, location, starts_at (future ISO timestamp), category (Volunteer drive, Workshop, Meetup, Sports, Arts & culture, Other), interest_tags (normalized array), city, mode (In person/Online), organization_name (optional), participant_limit (1–500, default 50). The browser requires tags and a city for in-person activities. Older API clients may omit tags/city; untagged events remain browsable but are not recommended. Legacy records without a capacity use a 500-person ceiling. Explicit empty interest_tags are invalid.

List filters: q (title/description/interests/city), category, scope=all|joined|organizing and pagination. Organizing includes past activities; other scopes show upcoming ones. A join retry cannot duplicate a registration. Concurrent joins cannot exceed capacity; edits cannot reduce capacity below current attendance or edit an activity that has started. Names of participants are visible only to the organizer. Organizer edits retain existing registrations; deletion removes the event and embedded registrations. Activity changes do not send notifications.

Activity suggestions require at least one shared normalized interest tag. They exclude own, joined, full and past activities. Local preference includes exact matching city names (case/outer-whitespace insensitive) and online activities; this is not geographic distance matching. Among up to 500 upcoming eligible records, order by shared-interest count, same city, start time and ID. Return six. These are transparent content matches, separate from the saved K-Means/Random Forest models; no fabricated percentage or semantic understanding of arbitrary related words is claimed. The shared suggested tags in profile/activity forms help users describe interests consistently.

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
