# Validation performed — 10 October 2026

Environment: Windows, Python 3.14.7, Node.js 24.19.0, XAMPP MariaDB 10.4.32. Dependency versions are recorded in `backend/requirements.lock.txt` and `frontend/package-lock.json`.

| Check | Actual result |
|---|---|
| Default backend Pytest suite | 19 passed; 3 explicitly skipped (one real-provider test, two MySQL-only concurrency tests) |
| XAMPP/MariaDB integration suite | 20 passed against newly generated disposable test schemas |
| MariaDB migration checks | Upgrade, no schema drift, downgrade to base and re-upgrade completed successfully |
| Chroma persistence | Real Chroma upsert/query, owner/document metadata filtering, reopen and delete passed |
| Real PDF extraction | Actual PyMuPDF-generated and parsed PDF upload/worker tests passed |
| Frontend React Testing Library | 5 passed |
| Frontend strict TypeScript + Vite build | Passed; production `frontend/dist` generated |
| npm dependency audit | 0 known vulnerabilities after patched Vitest upgrade |
| Python bytecode compilation | app, migrations and tests compiled successfully |
| Browser smoke check | Local login screen rendered against the running backend; narrow responsive layout inspected |
| Real model embeddings/inference | NOT executed: Ollama is not installed/running and no external provider was configured |

The application MySQL schema was created with a dedicated local account, migrations applied and roles/permissions/default limits initialized. No administrator password or runtime sample documents were seeded. An ignored `.env` was generated locally without printing secrets. API, worker and frontend were launched locally. Running processes for this session are development processes, not an installed Windows service.

The first validation runs found and corrected:

- Invalid PyMuPDF opens retained Windows file handles; validation now opens bounded bytes and rejected uploads can be removed.
- MariaDB 10.4 lacks `SKIP LOCKED`; the single-worker queue now uses compatible ordinary row locks.
- MySQL FK-supporting indexes cannot be dropped independently during downgrade; tables now drop in reverse dependency order, removing their indexes with them.
- Timestamp columns now preserve six microsecond digits on MySQL/MariaDB for stable ordering and exact activity deadlines.
- Quota transactions use `READ COMMITTED` with owner locks; concurrent uploads and questions were tested to enforce quotas.
- Initial Vitest dependency advisories were resolved by upgrading to a patched version.

The Chroma dependency emitted one Python 3.14 deprecation warning about `asyncio.iscoroutinefunction`. Its real persistence test passed. No warning was suppressed and no live AI result is claimed.

To complete live-provider acceptance, configure/install Ollama and run the opt-in test in [TESTING.md](TESTING.md). To use the admin dashboard, create an administrator through the interactive `python -m app.cli create-admin` command. Do not treat the local smoke check as a full authenticated browser or production penetration test.
