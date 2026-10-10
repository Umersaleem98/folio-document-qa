# Security and retention policy

## 24-hour inactivity retention

- All persisted DATETIME values are naive UTC; API timestamps explicitly include `Z`. MySQL connections set the session time zone to `+00:00`.
- New conversations expire 24 hours after creation. Every successfully committed question/answer sets `last_activity_at` to the current UTC time and `expires_at` to exactly 24 hours later.
- Listing, opening, failed AI calls and rejected requests never extend expiry. A question that finishes after the previous expiry is rejected rather than reviving the conversation.
- Every conversation read/write checks owner and `expires_at > now`. At the deadline, API access ends immediately even if the worker is stopped. The UI also clears visible conversation content at the deadline, but backend checks are authoritative.
- The worker independently sweeps on startup and every `CLEANUP_INTERVAL_SECONDS` (default 60). FastAPI startup runs an additional sweep. An external scheduled `python -m app.cli cleanup` can run as redundant cleanup.
- A single SQL delete cascades to messages and source references. There is no chat vector index, conversation cache, chat file, or provider conversation object to clean up. Only original document content is embedded. Worker restarts retry from durable SQL state.
- Physical row removal normally follows expiry within the configured sweep interval; an in-flight transaction holding a row lock can postpone removal until that transaction ends. If services are stopped or unavailable, access still fails/denies and deletion runs when services resume. This is logical deletion, not a claim of forensic erasure from database pages, SSD cells or in-flight client memory.
- No question, answer, excerpt, provider response, password or PDF text is written to application or audit logs. Validation errors omit original input. Disable request-body logging in reverse proxies, telemetry and error collectors; run Uvicorn with `--no-access-log` as documented.
- Usage/audit records retain IDs, action names, counts and UTC dates; they do not retain chat content or conversation titles. Documents and accounts remain until separately managed by their owners/admins.

## Backups and external providers — explicit exceptions

The application does not create backups. **Do not include `conversations`, `messages` or `sources` in MySQL logical backups or exported reports.** Full database snapshots, MySQL binary logs, OS page files, volume snapshots or third-party monitoring may retain deleted content outside the application's control. If you enable those, you must document their actual retention and erasure procedure as an exception before promising users the policy. A table exclusion approach needs a tested restore runbook; disable or separately expire content-bearing binary logs/snapshots according to your deployment policy. Account/document-only backups can exclude all three chat tables.

Default Ollama uses a local model endpoint and no remote model API. Configure the Ollama host not to log or persist prompts. An `openai-compatible` provider receives the current question and selected PDF chunks; embedding requests also send document chunks. External provider policies may retain these beyond 24 hours. Verify contractual retention/zero-data-retention settings and obtain an appropriate user-facing disclosure before enabling remote providers. There is no provider-side delete API implemented by this project. No zero-retention guarantee is made for arbitrary compatible endpoints.

The optional portable launcher keeps models in ignored `backend/data/models`, binds Ollama to loopback, disables cloud inference and disables request-body debug logging. The application uses the API without the Ollama interactive CLI, so it does not create interactive chat history. Embedding models unload after requests to reduce memory pressure. The runtime, model cache and vendor download helpers are outside chat retention because they contain model binaries rather than chat content.

## Authentication and access

JWTs expire after 30 minutes by default and are stored in HttpOnly SameSite=Strict cookies. There is no localStorage token. JWT session IDs are stored in SQL, enabling immediate logout revocation. Password changes, suspension and role assignment invalidate active sessions. Role permissions are loaded from SQL on every request. Registration accepts no role field, and always assigns the immutable `user` role. First admin creation is a local CLI action with an interactive password prompt, never a public HTTP endpoint.

Unsafe authenticated requests require a matching CSRF cookie/header. Unsafe requests with an unapproved Origin are denied, including login/registration. Only explicit CORS origins are allowed. In production set `ENVIRONMENT=production`, `COOKIE_SECURE=true`, use HTTPS, and serve frontend/API under the same origin. The frontend is a protected route experience; backend authorization is independently enforced. Admin monitoring exposes job IDs/status rather than original PDF filenames/content; administrators do not receive a bypass to private document/chat routes.

Database-backed auth/request limits survive restarts. Upload and daily question quota operations serialize against the owner row. Daily quotas reset at 00:00 UTC. Admin user/audit endpoints return at most 100 records with an `offset` query parameter. Built-in roles are immutable; custom permissions can be edited.

## Storage and PDF handling

Only UUID storage filenames are used. Original filenames are display metadata. PDF byte limits, signature/MIME/extension checks, encrypted PDF rejection, structural validation, maximum page count and extracted character count are enforced. A global streamed request cap is 101 MB. Multipart parsing may spool uploads temporarily; keep the OS temp directory private and on a volume with adequate capacity. PDFs are served as attachments behind authorization, avoiding active PDF content in the application origin. Scan uploads before processing if your deployment requires malware inspection. Scanned/image-only PDFs require external OCR; this project does not fabricate extracted text.

Keep the private `data/` directory and `.env` out of web roots and source control. Restrict Windows ACLs to the service account. Worker deletion retries after service failure. Document deletion denies access immediately and erases associated chats, then removes original file and vectors. Do not change embedding model/version with existing indexes without scheduling reindexing; the fingerprinted collection avoids mixing incompatible vectors, but old collections need manual operational retirement after verified reindexing.

## Grounding and prompt injection

Documents are untrusted data. The LLM receives fixed system instructions, source data in structured JSON, no tools, no privileged credentials, and no cross-user content. Retrieval is constrained to SQL-authorized owner/document IDs. A deterministic backend check only accepts exact contiguous quotations from retrieved chunks and rejects invented excerpts or malformed source identifiers. Generated explanatory prose is never returned. Text renders in React as escaped plain text without `dangerouslySetInnerHTML`. A malicious PDF can still contain misleading statements or quoted instructions; validation proves quote provenance, not the truth of the document or semantic relevance. Users must inspect evidence. Configure distance thresholds with representative documents.

## Worker supervision

Production requires supervision of both API and worker. Configure Windows Task Scheduler to launch `python.exe -m app.worker` at startup, set the working directory to `backend`, restart on failure, disallow concurrent instances, and disable the default three-day execution limit. The worker's retention sweep runs independently of embedding jobs. Monitor last successful cleanup operationally without capturing payloads. Run a redundant scheduled `python -m app.cli cleanup` at least every minute if desired. The database must be available when tasks launch; worker retries transient failures.

This local implementation has no email verification, email password-reset delivery, antivirus scanner, OCR engine, distributed Chroma service, cloud deployment or enterprise observability integration. These are explicit extension points, not simulated features.
