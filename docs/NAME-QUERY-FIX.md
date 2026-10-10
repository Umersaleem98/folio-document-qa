# Short resume question verification

The short queries "my name" and "tell me aboiut my name" previously missed the resume header because their embedding distances exceeded the configured cutoff. They now retrieve using an explicit full-name query. Page-one uppercase name headings followed by a professional title can produce a direct cited answer from the exact PDF text. This uses neither the user's profile nor the document filename to infer a name. Other evidence selection permits short exact quotes and still rejects excerpts absent from retrieved text.

Executed on 2026-10-10:

- Backend suite before adding the hosted-adapter test: 23 passed, 3 skipped.
- Real local AI integration plus document/security availability tests: 10 passed, including a generated resume and both short queries.
- Both reported queries through the actual Vite API proxy against the user's existing PDF: HTTP 200 with the correct page-one name citation. The temporary verification conversation was deleted.

Initial sandboxed test execution failed to open its temporary SQLite files; the same suite succeeded with the required filesystem access. A Chroma Python deprecation warning remains.

Independent CHAT_PROVIDER, CHAT_BASE_URL and CHAT_API_KEY settings allow hosted chat with local embeddings without changing the vector collection. README provides the Groq configuration. Follow-up on 2026-10-10: configured a user-supplied key only in the ignored backend .env. The account models endpoint returned qwen/qwen3.8-27b; the previously suggested Llama identifier was unavailable. Verified authenticated evidence selection and both live PDF integration tests with Groq chat and local embeddings (2 passed). Remote provider retention remains an exception to the application's chat policy as documented in SECURITY-AND-RETENTION.md.
