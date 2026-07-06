# Nya AI — Development Guide

---

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose (for MongoDB)
- npm or bun

---

## Repository Setup

The project has three independent repositories plus a shared database folder:

```
nya-ai/
├── database/              # MongoDB — shared infra
├── nyaai-frontend/        # React SPA
├── nyaai-backend/         # FastAPI server
└── nyaai-ai/              # AI service
```

Each has its own `.git`. The parent `wsuitsindustries` repo tracks the `products/nya-ai/` folder.

---

## Development Setup

### 1. Start MongoDB

```bash
cd database
docker compose up -d
```

MongoDB on `localhost:27017`, Mongo Express admin UI on `http://localhost:8081`.

### 2. Backend

```bash
cd nyaai-backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit JWT_SECRET, MONGO_URI if needed

# Run
python src/backend/main.py
```

Backend runs on `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd nyaai-frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`. Proxies `/api` → `localhost:8000`.

### 4. AI Service

```bash
cd nyaai-ai
cp .env.example .env
# Set LLM_API_KEY for your provider
```

The AI service is imported by the backend at runtime — no separate server needed.

### 5. Start Script

```bash
./start.sh
```

Starts both backend and frontend in parallel.

---

## Folder Structure

### Frontend (`nyaai-frontend/src/`)

```
src/
├── App.tsx                    — Root: providers + router
├── main.tsx                   — Entry point
├── index.css                  — Tailwind v4 + animations + brand theme
├── components/
│   ├── Buckets.tsx            — Document management page
│   ├── Chat.tsx               — Chat messages + input
│   ├── Settings.tsx           — Settings modal
│   ├── Sidebar.tsx            — Navigation sidebar
│   └── ui/                    — Reusable primitives
│       ├── ErrorBoundary.tsx
│       ├── NLogo.tsx
│       ├── PageLoader.tsx
│       └── Toggle.tsx
├── context/
│   ├── AuthContext.tsx         — Auth state
│   └── ThemeContext.tsx        — Theme state
├── hooks/
│   └── useApi.ts              — Chat hook + health hook
├── pages/
│   ├── Dashboard.tsx          — Authenticated shell
│   ├── Landing.tsx            — Public landing + demo
│   ├── Login.tsx              — Split-screen auth
│   ├── Privacy.tsx
│   ├── Terms.tsx
│   └── Contact.tsx
├── services/
│   └── api.ts                 — HTTP client
├── types/
│   └── index.ts               — TypeScript interfaces
└── utils/
    └── storage.ts             — localStorage helpers
```

### Backend (`nyaai-backend/src/`)

```
src/backend/
├── __init__.py
├── main.py                    — FastAPI app
├── config.py                  — Environment variables
├── database.py                — MongoDB connection
├── middleware/
│   └── auth.py                — JWT creation + verification
├── models/
│   └── schemas.py             — Pydantic models
├── routers/
│   ├── auth.py                — /auth/* endpoints
│   ├── chat.py                — /chat endpoint
│   ├── documents.py           — /documents/* endpoints
│   ├── search.py              — /search endpoint
│   └── upload.py              — /upload endpoint
└── services/
    └── document.py            — Document retrieval service
```

### AI Service (`nyaai-ai/src/`)

```
src/ai/
├── __init__.py
├── chunking.py                — Text splitting
├── embeddings.py              — Hash-based embeddings (placeholder)
├── llm.py                     — LLM provider abstraction
├── prompts.py                 — System prompts
├── rag.py                     — RAG pipeline
└── retrieval.py               — Cosine similarity search
```

---

## Coding Conventions

### TypeScript / React

- Functional components with explicit prop interfaces
- `useCallback` for handlers passed as props
- `useId` for SVG gradient IDs (prevents conflicts)
- Default exports for components, named exports for utilities
- Tailwind classes: base before `dark:` variant
- Import order: React → libraries → project modules

### Python

- Async/await throughout (FastAPI + motor)
- Type hints on all function signatures
- Pydantic models for request/response validation
- Router functions use `Depends()` for auth
- Env vars read via `os.getenv()` with defaults in `config.py`

### CSS

- Tailwind v4 utility classes preferred
- Custom animations in `index.css` with `@keyframes`
- Brand colors via `@theme` tokens
- Dark mode via `@custom-variant dark`

---

## Environment Variables

### `nyaai-backend/.env`

| Variable | Default | Description |
|---|---|---|
| HOST | `0.0.0.0` | Server bind address |
| PORT | `8000` | Server port |
| MONGO_URI | `mongodb://localhost:27017` | MongoDB connection string |
| MONGO_DB | `nyaai` | Database name |
| JWT_SECRET | *(required)* | Secret for signing JWT tokens |
| ACCESS_TOKEN_EXPIRE_MINUTES | `1440` | Token expiry in minutes |
| CORS_ORIGINS | `http://localhost:5173` | Comma-separated allowed origins |

### `nyaai-ai/.env`

| Variable | Default | Description |
|---|---|---|
| LLM_PROVIDER | `openai` | Provider name |
| LLM_API_KEY | *(required)* | API key |
| LLM_BASE_URL | `https://api.openai.com/v1` | API base URL |
| LLM_MODEL | `gpt-4o-mini` | Model name |
| LLM_MAX_TOKENS | `1024` | Max response tokens |
| LLM_TEMPERATURE | `0.7` | Response temperature |

---

## Repository Responsibilities

### Frontend
- User interface and interaction
- State management (auth, theme, chat, settings)
- API communication via HTTP
- localStorage persistence for conversations and settings

### Backend
- HTTP API server
- Authentication (JWT + bcrypt)
- MongoDB persistence
- File upload handling and validation
- RAG orchestration (calls AI layer)

### AI Layer
- Document chunking
- Embedding and retrieval
- LLM communication
- Prompt assembly
- Response generation

---

## How They Communicate

```
Frontend ──HTTP──▶ Backend (port 8000)
                       │
                       ├── MongoDB (port 27017)
                       │
                       └── Python import → AI Layer (in-process)
                                              │
                                              └── HTTP → LLM API
```

- Frontend calls backend via fetch API (proxied through Vite in dev)
- Backend imports AI service directly (`sys.path.insert` in `main.py`)
- AI service calls LLM provider via `httpx.AsyncClient`
- No message broker, no queue, no RPC between backend and AI

---

## Build & Deploy

### Frontend Build

```bash
cd nyaai-frontend
npm run build     # Outputs to dist/
```

Static files in `dist/` — deploy to any static host (Vercel, Netlify, S3, etc.).

### Backend Deploy

```bash
cd nyaai-backend
pip install -r requirements.txt
python src/backend/main.py
```

Requires Python 3.11+, MongoDB access, and LLM API key.

### Production Considerations

- Set `JWT_SECRET` to a strong random value
- Set `CORS_ORIGINS` to your frontend domain
- Configure a production MongoDB instance
- Set `LLM_API_KEY` securely (not in version control)
- Use a process manager (systemd, supervisor) for the backend
- Add reverse proxy (nginx, Caddy) for TLS termination
