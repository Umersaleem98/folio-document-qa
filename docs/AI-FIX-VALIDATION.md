# Local AI service fix — 10 October 2026

The original processing error was reproduced: the configured Ollama endpoint was unreachable because no runtime was installed/running. The uploaded two-page PDF was intact and extractable; the failure was at embedding generation.

## Changes

- Installed official Ollama 0.40.2 CPU components from the vendor Windows ZIP into ignored project data. Every extracted entry was checked for expected length/CRC and confined to the runtime directory. The superseded large installer transfer was cancelled without changing other downloads.
- Started loopback-only local inference with cloud access disabled and models stored in `backend/data/models`.
- Downloaded real `nomic-embed-text` and `qwen2.5:0.5b` models. Only about 1.2 GB of system RAM was available, so a compact chat model was selected. Larger models require more free memory and can improve semantic evidence selection.
- Added authenticated `/api/ai/status`, an actionable library warning, and safe errors for connection failure, missing models, authentication rejection and timeouts. Provider response bodies and document text are not included in those errors.
- Applied [Nomic's required task prefixes](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5): `search_document:` for corpus chunks and `search_query:` for questions. Existing PDFs were queued for reindexing with their files preserved and deterministic chunk IDs replaced.
- Constrained Ollama evidence output with JSON Schema and allowed source indices. The first live test showed that the small model confused evidence numbering with source numbering; the schema and explicit source IDs corrected this. Backend exact-quote validation remains mandatory.
- Embedding requests unload their model after use to reduce memory pressure.
- Added portable startup/download helpers and updated the README's AI terminal instructions.

## Executed checks

| Check | Result |
|---|---|
| Backend regression suite | 22 passed, 3 explicit skips for separately opt-in live AI and MySQL concurrency |
| Real-provider integration plus focused PDF/RAG/availability tests | 8 passed, including actual local inference and cited answer |
| Frontend React Testing Library | 5 passed |
| TypeScript + Vite production build | Passed |
| Running frontend/API proxy | Login, AI readiness and original document status verified through localhost:5173 |
| Original failed upload | Retried and reindexed successfully; ready status, 2 pages, no processing error |

The live-provider check used a generated test PDF in an isolated test database, actual PyMuPDF extraction, real embeddings, actual Chroma storage/retrieval, actual model inference, verified quotes, page citations and deletion. The passing live run supersedes the initial build report's unavailable-provider limitation. It is a representative acceptance check, not a guarantee of perfect semantic selection for every document/question.

## Restarting

Keep the AI terminal running alongside the API, worker and frontend:

```powershell
cd 'D:\Web Works\document-qa\backend'
.\.venv\Scripts\python.exe start_local_ai.py
```

Models are already downloaded on this workstation. If the cache is missing on a new installation, run `download_ai_models.py` from another backend terminal after the AI server is listening. Exact commands for all components are in the README.
