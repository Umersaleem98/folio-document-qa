# LinkedIn launch post

I built Folio — an AI-powered document Q&A application that turns PDFs into a searchable knowledge library. 📄💬

The goal: make answers easier to verify by showing the document, page number, and supporting excerpt behind each response.

What I implemented:

• PDF upload, text extraction, chunking, and semantic search
• Grounded answers with source citations and an explicit response when evidence is insufficient
• Groq chat integration with local Ollama embeddings and ChromaDB
• JWT authentication, Argon2id password hashing, and document ownership checks
• An admin dashboard for accounts, roles, limits, usage, and audit records
• Backend-enforced chat expiry after 24 hours of inactivity
• A responsive React interface and automated backend/frontend tests

Stack: Python · FastAPI · SQLAlchemy · MySQL · React · TypeScript · Vite · Bootstrap · PyMuPDF · ChromaDB

One of the most useful lessons: choosing an LLM is only part of the work. Retrieval quality, evidence validation, authorization, and dependable cleanup all matter when building a document Q&A system.

GitHub: https://github.com/Umersaleem98/folio-document-qa

I’d love feedback from developers working on RAG applications. What would you improve or add next?

#AI #RAG #FastAPI #ReactJS #Python #FullStackDevelopment #DocumentAI

---

Publish only after the repository has been created and pushed. A private repository requires explicit access for readers.
