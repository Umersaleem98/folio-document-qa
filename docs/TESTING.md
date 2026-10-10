# Executable verification

## Automated API/security suite

```powershell
Set-Location 'D:\Web Works\document-qa\backend'
.\.venv\Scripts\python.exe -m pytest -q
```

The default run uses a new temporary SQLite database with foreign keys enabled and the real SQLAlchemy model/session layer. PDFs are generated with real PyMuPDF and parsed by the actual upload/extraction code. A real persistent Chroma test checks explicit-vector insertion, tenant/document filtering, reopening storage and deleting only the selected document. It does not pretend those fixed test vectors are real model embeddings. Deterministic AI unit tests inject test-only doubles to validate provenance checks and unsupported-answer behavior. All runtime embeddings and LLM evidence selection call a configured real endpoint.

Coverage includes public role escalation rejection, Argon2id hashes, CSRF, Origin denial, revoked/expired JWT sessions, suspensions, password-session invalidation, validation privacy, durable login throttles, private document/conversation isolation, PDF rejection, processing, document deletion, exact retention boundaries, message/source cascades, restart cleanup, activity extension, failed requests, expiry during in-flight answers, crashed job lease recovery and cleanup while a document job is stalled. Two MySQL-only tests also issue simultaneous requests to verify upload and daily question quotas cannot be bypassed; they are explicitly skipped on SQLite.

## XAMPP/MySQL integration

For a default local XAMPP installation with passwordless local root, this helper creates a **new generated disposable schema**, applies/checks migrations, runs the API/security/PDF suite against MariaDB, downgrades/reapplies migrations, and finally removes only its generated schema. It never uses or modifies `document_qa`:

```powershell
Set-Location 'D:\Web Works\document-qa\backend'
.\.venv\Scripts\python.exe verify_xampp.py
```

For a secured installation, create a separate disposable database whose name ends with `_test`, grant your test account schema privileges, then pass its URL directly in your local environment:

```powershell
$env:MYSQL_TEST_DATABASE_URL='mysql+pymysql://YOUR_TEST_ACCOUNT:YOUR_ENCODED_PASSWORD@127.0.0.1:3306/document_qa_test?charset=utf8mb4'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:MYSQL_TEST_DATABASE_URL
```

**This test suite drops/recreates all application tables in the selected test database.** It validates the `_test` suffix to refuse ordinary production names, but you must still select an exclusively disposable schema. Do not point it at user data. Normal runs without this variable do not touch the real MySQL application database.

## Real provider integration (explicit opt-in)

Start your configured real provider and download/configure the named models. Remote mode sends generated test PDF text/questions to that provider and may incur API charges. Default local Ollama mode performs real embeddings and inference locally.

```powershell
Set-Location 'D:\Web Works\document-qa\backend'
$env:RUN_LIVE_AI_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_live_provider.py -q
Remove-Item Env:RUN_LIVE_AI_TESTS
```

This exercises actual PDF upload → worker extraction → embeddings → persistent Chroma → semantic query → LLM evidence selection → backend quote checks → page citations → document/chat deletion. It fails if the provider does not return grounded evidence. Ordinary tests explicitly skip this case when no provider is configured, and that skip must not be described as a passed live AI test.

## Frontend

```powershell
Set-Location 'D:\Web Works\document-qa\frontend'
npm ci
npm test
npm run build
npm audit
```

React Testing Library exercises private-route redirection, strict registration payloads, visible retention disclosure, source/page rendering with script text escaped, and document processing status. Build runs strict TypeScript plus Vite production bundling. API functions are isolated with fetch doubles only inside tests. Browser checks should also cover real login, upload, status polling, history, source downloads, responsive navigation and administrative permission changes with a disposable account and a configured provider.

See [VALIDATION.md](VALIDATION.md) for actual results from this workstation. No external-service pass is implied by unit results.
