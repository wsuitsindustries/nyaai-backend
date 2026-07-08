import asyncio
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

AI_DIR = Path(__file__).resolve().parent.parent.parent.parent / "nyaai-ai"

sys.path.insert(0, str(AI_DIR / "src"))

from dotenv import load_dotenv
load_dotenv(AI_DIR / ".env")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.config import HOST, PORT, CORS_ORIGINS
from backend.database import connect_db, close_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    from ai.embeddings import embed
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, lambda: __import__("asyncio").run(embed("warmup")))
    yield
    await close_db()


app = FastAPI(
    title="Nya AI API",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
