# Nya AI — MVP Audit Report

**Date:** 2026-07-06
**Scope:** Complete codebase audit against Master Strategy Document
**Status:** MVP-ready with gaps

---

## 1. MVP Feature Audit

| MVP Feature | Status | Notes |
|---|---|---|
| Secure login | ✅ Complete | JWT + bcrypt, Sign In / Sign Up toggle |
| Registration | ✅ Complete | name + email + password, min 6 char validation |
| Session management | ✅ Complete | localStorage token, auto-restore on refresh |
| Upload documents | ✅ Complete | File validation (10MB, ext filter), chunking, status steps |
| Process and index | ✅ Complete | Chunking + FastEmbed (BAAI/bge-small-en-v1.5) semantic embeddings |
| Ask natural language questions | ✅ Complete | Chat input → RAG pipeline → response |
| Accurate grounded answers | ✅ Complete | Real semantic embeddings now power retrieval |
| View citations | ✅ Complete | Source filename + snippet rendered in expandable section |
| Continue conversations | ✅ Complete | Conversation history in localStorage, grouped by date |
| Manage uploaded knowledge | ✅ Complete | Buckets page: list, delete, reindex documents |
| Streaming responses | ❌ Missing | Backend has `complete_stream()` but frontend uses non-streaming |
| Markdown rendering | ✅ Complete | CSS styles for code, lists, bold in `.message-content` |
| Processing status | ✅ Complete | Upload shows status steps (uploading/extracting/chunking/embedding) |
| Semantic search | ✅ Complete | FastEmbed (BAAI/bge-small-en-v1.5) — 384-dim ONNX embeddings |
| Multi-document retrieval | ⚠️ Partial | `get_document_chunks()` returns all chunks; no user_id filtering |
| Source citations | ❌ Missing | `Source` model exists, backend returns them, frontend ignores |
| User management | ❌ Missing | No admin endpoints, no roles |
| Workspace management | ❌ Missing | No multi-tenant isolation |
| Document overview | ✅ Complete | Buckets page with status, size, date, actions |

---

## 2. Technical Debt

### Immediate (blocks MVP)

| Item | Impact |
|---|---|
| ~~Hash-based embeddings are placeholders~~ | ✅ Fixed — FastEmbed semantic embeddings |
| ~~Frontend ignores sources in response~~ | ✅ Fixed — sources rendered with filename + snippet |
| ~~MongoDB not running in dev~~ | ✅ Fixed — Docker Compose up |
| No error boundary in production path | `/*` route wraps in ErrorBoundary but `/login` and public pages use it correctly |

### Soon (should fix before wider release)

| Item | Impact |
|---|---|
| Backend `routers/__init__.py` and `services/__init__.py` are empty | Minor, works but untidy |
| ~~No `.gitignore` for `__pycache__` in backend~~ | ✅ Already existed |
| `vite.config.ts` strips `/api` prefix | Works but confusing — could mount backend routes at `/api` prefix |
| `config.py` reads env vars directly | No validation, no defaults, no type coercion |
| `Chat.tsx` is 520 lines | Hard to maintain, could split into smaller components |
| ~~No request validation for chat message length~~ | ✅ Fixed — 10k limit on both FE + BE |
| Upload has no progress indicator | Large files appear stuck |
| Demo mode uses hardcoded responses | Sample data label added but still fake |

### Later

| Item | Impact |
|---|---|
| No tests anywhere | Risk of regressions |
| No CI/CD pipeline | Manual deploy only |
| No rate limiting | Abuse potential |
| No audit logging | Enterprise requirement |
| `start.sh` uses `--break-system-packages` | Kali-specific workaround |
| Embeddings in `embeddings.py` use MD5 | Not production-grade |
| Frontend uses `crypto.randomUUID()` for IDs | Fine for MVP, no backend verification |

---

## 3. UX Improvements

| Issue | Recommendation |
|---|---|
| No citations shown | Render `Source[]` as expandable citations below assistant messages |
| No empty state for Buckets | Show "No documents uploaded yet" with upload CTA |
| Login has no "forgot password" | Add link (can link to placeholder for MVP) |
| No keyboard shortcut hints | Show `⌘K`, `⌘N`, `⌘,` in tooltips |
| Demo mode doesn't explain RAG | Add note: "Responses are from sample company documents" |

---

## 3b. Recently Fixed Items

| Item | Fix |
|---|---|
| Rate limiting on upload | ✅ In-memory 10 req/60s per IP, returns 429 |
| Chat message length validation | ✅ 10,000 char max on both FE + BE |
| Demo responses labeled as sample | ✅ Amber "Sample data" badge in demo header |
| Citations now show document name + preview | ✅ Source filename + 120-char snippet rendered |
| Semantic search (hash → FastEmbed) | ✅ BAAI/bge-small-en-v1.5 (384-dim, ONNX) |

---

## 4. Product Alignment

| Screen | Verdict | Notes |
|---|---|---|
| Landing | ✅ Aligned | "What can I help with?" positions as knowledge tool |
| Login | ✅ Aligned | Split-screen with enterprise branding |
| Chat | ✅ Aligned | ChatGPT-like interaction, purple Nya branding |
| Sidebar | ✅ Aligned | Conversation history, knowledge management, settings |
| Buckets | ✅ Aligned | Document management with status tracking |
| Settings | ✅ Aligned | Theme, input preferences |
| Demo mode | ⚠️ Partial | Hardcoded responses undermine "accurate grounded answers" promise |

---

## 5. Backend Gaps

| Area | Status |
|---|---|
| Auth (JWT + bcrypt) | ✅ Complete |
| Chat endpoint | ✅ Complete with user_id scoping |
| Upload endpoint | ✅ Complete with validation |
| Documents CRUD | ✅ Complete |
| Search endpoint | ⚠️ Hash embeddings |
| MongoDB persistence | ⚠️ No running instance |
| Centralized error handling | ❌ Missing — HTTPExceptions scattered |
| Request/response validation | ⚠️ Partial — ChatRequest has no length limits |
| Rate limiting | ❌ Missing |

---

## 6. AI Gaps

| Area | Status |
|---|---|
| Chunking | ✅ Complete |
| RAG pipeline | ✅ Complete |
| LLM integration | ✅ Complete (6 providers) |
| Prompt management | ✅ Complete |
| Retrieval | ✅ Complete — semantic with FastEmbed |
| Embeddings | ✅ Complete — BAAI/bge-small-en-v1.5 (384-dim, ONNX) |
| Citation generation | ✅ Complete — filename + snippet in sources |

---

## 7. Immediate Action Items (MVP Gate)

- ✅ Citations in Chat UI — rendered with filename + snippet
- ✅ MongoDB running — Docker Compose with `database/`
- ✅ Buckets empty state — icon + upload CTA
- ✅ Rate limiting on upload — 10 req/60s per IP
- ✅ Chat message length validation — 10k limit FE + BE
- ✅ Demo sample label — amber "Sample data" badge
- ✅ Semantic embeddings — FastEmbed (BAAI/bge-small-en-v1.5) replaces hash trigrams

## 8. Next Action Items

1. **Streaming responses** — `complete_stream()` exists in backend but unused by frontend
2. **Real embeddings in init.js** — index with `embedding` field for hybrid search
3. **Upload progress indicator** — polling `/documents/{id}/status` during processing
4. **Vite API prefix** — mount backend routes at `/api` prefix instead of stripping it
5. **Demo mode with real RAG** — let demo actually hit the backend with sample docs
6. **Tests** — pytest for backend, vitest for frontend
