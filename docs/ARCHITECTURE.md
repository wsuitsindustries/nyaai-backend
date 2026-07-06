# Nya AI — Architecture

**Version:** 1.0 (MVP)
**Status:** Reflects current implementation

---

## System Architecture

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│              │       │                  │       │              │
│  Frontend    │ HTTP  │    Backend       │import │   AI Layer   │
│  React 19    │──────▶│  FastAPI/Python  │──────▶│  Python      │
│  Vite 8      │◀─────│  Port 8000       │       │  RAG         │
│  Tailwind v4 │       │                  │       │              │
│              │       │                  │       └──────┬───────┘
└──────────────┘       └────────┬─────────┘              │
                                │                        │
                          ┌─────▼─────┐           ┌──────▼──────┐
                          │  MongoDB  │           │   LLM API   │
                          │  (motor)  │           │  (Groq/OpenAI)
                          └───────────┘           └─────────────┘
```

---

## Frontend Architecture

### Component Tree

```
<App>
  <ThemeProvider>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          /login          → <Login />
          /privacy        → <Privacy />
          /terms          → <Terms />
          /contact        → <Contact />
          /*              → <PageLoader /> <Dashboard />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </ThemeProvider>
</App>
```

### Dashboard Component Tree

```
<Dashboard>                              ← pages/Dashboard.tsx
  <Sidebar />                            ← Nav: new chat, search, conversations, buckets, settings, logout
  <Chat />                               ← Messages, input, edit, regenerate, attach
  — or —
  <Buckets />                            ← Document list, upload, delete, reindex
  <Settings />                           ← Modal: theme, enter-to-send, suggestions
```

### Data Flow

```
User Input
    ↓
Chat.tsx (form)
    ↓
useApi.ts (useChat hook)
    ↓
services/api.ts (fetch wrapper)
    ↓
POST /api/chat → Vite proxy → Backend /chat
    ↓
Response → useChat → setMessages (state)
    ↓
Chat.tsx re-renders
```

### State Management

- **Auth**: `AuthContext` — user email + token, localStorage-backed
- **Theme**: `ThemeContext` — dark/light/system, localStorage-backed + media query listener
- **Chat messages**: Local state in `useChat` hook (via `useState`)
- **Conversations**: localStorage (`nya-conversations`, `nya-msg-*`)
- **Settings**: localStorage (`nya-enter-send`, `nya-suggestions`)
- **Token**: localStorage (`nya-token`, `nya-email`)

---

## Backend Architecture

### Application Structure

```
main.py
├── lifespan (connect_db / close_db)
├── CORS middleware
├── Router includes
│   ├── auth      → /auth/*
│   ├── chat      → /chat
│   ├── upload    → /upload
│   ├── search    → /search
│   └── documents → /documents/*
└── Health check  → /health
```

### Request Flow

```
HTTP Request
    ↓
CORS Middleware
    ↓
Router
    ↓
Auth Dependency (optional — returns dict | None)
    ↓
Route Handler
    ├── Auth routes: validate credentials → return JWT
    ├── Chat routes:  retrieve chunks → call RAG → persist → return answer
    ├── Upload routes: validate file → chunk → store → return status
    ├── Search routes: retrieve chunks → return results
    └── Document routes: CRUD on documents collection
    ↓
Pydantic Response Model
    ↓
HTTP Response
```

### Routes Detail

| Route | File | Auth | DB Write | DB Read |
|---|---|---|---|---|
| POST /auth/register | `routers/auth.py` | No | users | users (check dup) |
| POST /auth/login | `routers/auth.py` | No | — | users |
| POST /chat | `routers/chat.py` | Optional | messages, conversations | — |
| POST /upload | `routers/upload.py` | Optional | documents, files, conversations | — |
| POST /search | `routers/search.py` | Optional | — | all chunks |
| GET /documents | `routers/documents.py` | Optional | — | documents |
| GET /documents/{id}/status | `routers/documents.py` | Optional | — | documents |
| DELETE /documents/{id} | `routers/documents.py` | Optional | documents, files | documents |
| POST /documents/{id}/reindex | `routers/documents.py` | Optional | documents | documents |

### JWT Auth Flow

```
Login/Register
    ↓
create_access_token({"sub": email, "name": name})
    ↓
Returns { access_token, token_type: "bearer", email, name }
    ↓
Frontend stores token in localStorage
    ↓
Subsequent requests include Authorization: Bearer <token>
    ↓
get_current_user() decodes JWT
    ├── Valid → returns {"sub": email, "name": name}
    └── Invalid/missing → returns None (auto_error=False)
```

---

## AI Layer Architecture

### RAG Pipeline

```
User Question
    ↓
answer_with_rag(question, chunks, use_llm=True)    ← rag.py
    ↓
retrieve_texts(question, chunks, top_k=5)           ← retrieval.py
    ↓
Cosine similarity scoring (hash-based embeddings)   ← embeddings.py
    ↓
Top-k chunks + sources
    ↓
build_prompt(question, chunks, sources)             ← prompts.py
    ↓
If use_llm=True:
  complete(prompt)                                   ← llm.py
    ↓
  LLM API call (Groq by default)                    ← httpx
    ↓
  Return (answer, relevant_chunks)
Else:
  Return (formatted_context, relevant_chunks)
```

### LLM Provider Abstraction

```
llm.complete(prompt, system_prompt) → str
llm.complete_stream(prompt, system_prompt) → AsyncGenerator[str]

Providers (configured via env vars):
  - openai    → api.openai.com
  - groq      → api.groq.com (default, active key set)
  - ollama    → localhost:11434
  - openrouter → openrouter.ai
  - together  → api.together.xyz
  - github    → models.inference.ai.azure.com
```

### Chunking Strategy

```
chunk_text(text, chunk_size=1000, overlap=200)
  ├── Split by paragraphs first
  ├── If paragraph > chunk_size, split by sentences
  ├── Overlap between consecutive chunks (default 200 chars)
  └── Return list of strings
```

---

## Database Schema (MongoDB)

### users
```json
{
  "_id": ObjectId,
  "id": UUID string,
  "name": string,
  "email": string (unique, lowercase),
  "password_hash": string (bcrypt),
  "created_at": datetime
}
```

### conversations
```json
{
  "_id": ObjectId,
  "id": UUID string,
  "user_id": string | null,
  "title": string,
  "created_at": datetime,
  "updated_at": datetime
}
```

### messages
```json
{
  "_id": ObjectId,
  "id": UUID string,
  "conversation_id": string,
  "user_id": string | null,
  "role": "user" | "assistant",
  "content": string,
  "sources": [{"title": string, "page": string|null, ...}],
  "created_at": datetime
}
```

### documents
```json
{
  "_id": ObjectId,
  "id": UUID string,
  "user_id": string | null,
  "filename": string,
  "size": number,
  "uploaded_at": datetime,
  "status": "uploading"|"extracting"|"chunking"|"embedding"|"ready"|"failed",
  "chunks": number,
  "conversation_id": string,
  "text": string,
  "chunk_texts": [string],
  "error": string | null
}
```

---

## Communication Patterns

### Frontend ↔ Backend
- HTTP via fetch API
- Auth token passed as Bearer header
- Vite dev server proxies `/api` → `localhost:8000` (strips `/api` prefix)
- No WebSocket — all requests are request/response

### Backend ↔ AI
- Direct Python import via `sys.path.insert`
- `from ai.rag import answer_with_rag`
- No RPC, no network call — in-process function call

### Backend ↔ MongoDB
- Async via `motor` (async MongoDB driver)
- `get_db()` returns database handle from connection pool
- Connection established in `lifespan` on startup

### AI ↔ LLM
- HTTP via `httpx.AsyncClient`
- OpenAI-compatible chat completions endpoint
- Configurable provider via environment variables
