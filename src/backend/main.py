import os
import sys
import logging
import time
from pathlib import Path
from contextlib import asynccontextmanager

AI_DIR = Path(__file__).resolve().parent.parent.parent.parent / "nyaai-ai"

sys.path.insert(0, str(AI_DIR / "src"))

from dotenv import load_dotenv
load_dotenv(AI_DIR / ".env")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from backend.config import HOST, PORT, CORS_ORIGINS, JWT_SECRET
from backend.database import connect_db, close_db

logger = logging.getLogger(__name__)

# ── Simple in-memory rate limiter ───────────────────────────────

_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT = 30  # requests
RATE_WINDOW = 60  # seconds
_last_rl_cleanup = 0.0


async def rate_limit_middleware(request: Request, call_next):
    global _last_rl_cleanup
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    timestamps = _rate_limit_store.get(client_ip, [])
    timestamps = [t for t in timestamps if now - t < RATE_WINDOW]
    if len(timestamps) >= RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})
    timestamps.append(now)
    _rate_limit_store[client_ip] = timestamps

    if now - _last_rl_cleanup > RATE_WINDOW:
        _last_rl_cleanup = now
        expired = [ip for ip, ts in _rate_limit_store.items() if max(ts) < now - RATE_WINDOW]
        for ip in expired:
            del _rate_limit_store[ip]

    return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Nya AI API",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENV", "development") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENV", "development") != "production" else None,
)

app.middleware("http")(rate_limit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.getenv("ENV", "development") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[origin.split("://")[-1].split(":")[0] for origin in CORS_ORIGINS],
    )

logger.info(f"JWT_SECRET is {'SET' if JWT_SECRET and JWT_SECRET != 'change-me-in-production' else 'NOT SET — using auto-generated'}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


from backend.routers import auth, chat, upload, search, documents

app.include_router(auth.router)
app.include_router(chat.router, tags=["chat"])
app.include_router(upload.router, tags=["upload"])
app.include_router(search.router, tags=["search"])
app.include_router(documents.router, tags=["documents"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True, reload_dirs=[str(Path(__file__).resolve().parent.parent)])
