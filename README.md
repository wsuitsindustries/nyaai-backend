# Nya AI — Backend API

FastAPI backend for the Nya AI enterprise knowledge agent. Handles chat, document upload, and search.

## Directory Structure

```
src/backend/
  main.py          FastAPI app entry point
  config.py        Environment configuration
  models/
    schemas.py     Pydantic request/response models
  routers/
    chat.py        POST /chat — answer questions with RAG
    upload.py      POST /upload — ingest documents
    search.py      POST /search — semantic search across chunks
  services/
    document.py    In-memory document store
    fake_ai.py     Rule-based response generator (placeholder for real LLM)
  middleware/
    auth.py        API key auth placeholder
tests/             Tests
```

## Quick Start

```bash
pip install -r requirements.txt
python -m src.backend.main
# or
uvicorn backend.main:app --reload
```

The API runs at `http://localhost:8000` with docs at `/docs`.

## Environment

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST`   | `0.0.0.0` | Bind address |
| `PORT`   | `8000`  | Server port |
| `NYA_API_KEY` | `""` | API key (optional, empty = open) |
