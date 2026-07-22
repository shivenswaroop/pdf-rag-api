# DocuQuery — PDF RAG API

Ask questions about uploaded PDF documents. Answers are grounded in retrieved document chunks; if the content is not in the documents, the system refuses instead of inventing an answer.

## Project overview

DocuQuery is a Retrieval-Augmented Generation (RAG) application:

1. **Upload** a PDF (single or bulk)
2. **Extract** text with PyMuPDF, **chunk** it, and **embed** with `BAAI/bge-small-en-v1.5`
3. **Store** vectors in a persistent **ChromaDB** collection
4. **Ask** a natural-language question → retrieve top chunks → answer with an LLM via **OpenRouter**
5. Return **page-level source citations** when evidence is found

A React UI (`frontend/`) provides document management, vector-store inspection, and Q&A.

```
PDF upload → extract → chunk → embed → ChromaDB
                                         ↓
User question → embed → similarity search → LLM (context-only) → answer + sources
```

## Tech stack

| Layer | Choice |
|-------|--------|
| API | Python 3.11+, FastAPI, Uvicorn |
| PDF | PyMuPDF |
| Chunking | LangChain `RecursiveCharacterTextSplitter` (500 / 100) |
| Embeddings | Sentence Transformers `BAAI/bge-small-en-v1.5` |
| Vector DB | ChromaDB (persistent under `vector_db/`) |
| LLM | OpenRouter (default free model `openai/gpt-oss-20b:free`, with free fallbacks) |
| Frontend | React + Vite + TypeScript |
| Containers | Docker + Docker Compose |

## Repository layout

```
app/                 FastAPI application
  routers/           upload, documents, chat
  services/          ingest, embeddings, vector store, LLM, registry
frontend/            React SPA
samples/             Sample PDFs for testing
storage/             Uploaded files + documents.json registry
vector_db/           ChromaDB persistence
Dockerfile           API image
docker-compose.yml   API + frontend
```

## Setup

### Prerequisites

- Python 3.10+ (3.11 recommended)
- Node.js 20+ (for the frontend)
- An [OpenRouter](https://openrouter.ai/) API key
- Docker (optional, for Compose)

### 1. Environment

```bash
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY=...
```

### 2. Backend (local)

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# From the project root:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000  
- Swagger: http://localhost:8000/docs  

First start downloads the embedding model from Hugging Face (~tens of MB) and may take a minute.

### 3. Frontend (local)

```bash
cd frontend
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev
```

Open http://localhost:5173

### 4. Docker Compose

```bash
cp .env.example .env   # set OPENROUTER_API_KEY
docker compose up --build
```

- API: http://localhost:8000  
- UI: http://localhost:5173  

Volumes persist `storage/` and `vector_db/`.

## Dependencies

Pinned in [`requirements.txt`](requirements.txt). Frontend dependencies are in [`frontend/package.json`](frontend/package.json).

Key Python packages: `fastapi`, `uvicorn`, `pymupdf`, `chromadb`, `sentence-transformers`, `langchain-text-splitters`, `openai`, `python-dotenv`.

## API documentation

Interactive docs: `/docs` (Swagger) and `/redoc`.

### `POST /upload/`

Upload and index one PDF (`multipart/form-data`, field `file`).

```bash
curl -X POST http://localhost:8000/upload/ \
  -F "file=@samples/benefits_policy.pdf"
```

Response:

```json
{
  "document_id": "uuid",
  "message": "PDF uploaded successfully.",
  "filename": "benefits_policy.pdf",
  "path": "storage/uploads/...",
  "page_count": 2,
  "chunk_count": 3,
  "uploaded_at": "..."
}
```

### `POST /upload/bulk/`

Upload multiple PDFs (field name `files`, repeated).

```bash
curl -X POST http://localhost:8000/upload/bulk/ \
  -F "files=@samples/benefits_policy.pdf" \
  -F "files=@samples/acme_widget_faq.pdf"
```

### `GET /documents/`

List all registered documents.

### `GET /documents/{document_id}`

Document metadata.

### `GET /documents/{document_id}/chunks`

Inspect chunks stored in ChromaDB (page, snippet, chunk index).

### `DELETE /documents/{document_id}`

Remove the PDF from disk, registry entry, and all related vectors.

### `POST /chat/`

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the eligibility criteria?", "document_id": null}'
```

Optional `document_id` scopes retrieval to one document.

Success with evidence:

```json
{
  "answer": "...",
  "sources": [
    { "page": 1, "document_id": "...", "snippet": "..." }
  ]
}
```

When retrieval is weak or empty:

```json
{
  "answer": "I cannot answer this question from the provided document content.",
  "sources": []
}
```

### `GET /health`

Liveness check.

## Sample PDFs

| File | Use for |
|------|---------|
| [`samples/benefits_policy.pdf`](samples/benefits_policy.pdf) | Eligibility / leave questions |
| [`samples/acme_widget_faq.pdf`](samples/acme_widget_faq.pdf) | Warranty / reset questions |

Example in-doc question: *“What are the eligibility criteria?”*  
Example out-of-doc question: *“What is the capital of France?”* (should refuse)

## Configuration (environment variables)

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Required for chat (alias: `HUNYUAN_API_KEY`) |
| `LLM_MODEL` | OpenRouter free model id (default `openai/gpt-oss-20b:free`; must end with `:free`) |
| `LLM_FALLBACK_MODELS` | Comma-separated free models tried on 429/404/503 |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `LOG_LEVEL` | Logging level (default `INFO`) |
| `RETRIEVAL_MAX_DISTANCE` | Max Chroma distance to accept a chunk (default `1.2`) |
| `VITE_API_BASE_URL` | Frontend → API base URL |

## Assumptions

- PDFs contain extractable text. Pure scanned/image PDFs without OCR are rejected with a clear error.
- Single-tenant local deployment; no authentication.
- One shared Chroma collection; optional per-document filter on chat.
- Free-tier OpenRouter models may rate-limit or change availability.
- Document registry (`storage/documents.json`) is the source of truth for the list API; files uploaded before this registry existed will not appear until re-uploaded.

## Design decisions

- **Grounding:** system prompt requires context-only answers; weak retrieval short-circuits to a refusal without calling the LLM.
- **Citations:** page numbers stored as chunk metadata and returned as `sources`.
- **Registry:** lightweight JSON index for list/delete without scanning Chroma for filenames.
- **Embeddings local:** no paid embedding API; model runs in-process (higher RAM, simpler ops).

## Future improvements

- OCR pipeline for scanned PDFs
- Conversation history / sessions
- Streaming (SSE) answers
- Authentication and per-user isolation
- Hybrid search (BM25 + dense)
- Unit/integration tests and CI
- Cloud deployment (e.g. Fly.io / Railway) with managed object storage
