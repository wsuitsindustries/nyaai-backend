import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from backend.models.schemas import UploadResponse
from backend.database import get_db
from backend.middleware.auth import get_current_user

router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "text/plain", "text/markdown", "text/csv",
    "application/json", "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60


def check_rate_limit(client_ip: str):
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = rate_limit_store[client_ip]
    timestamps[:] = [t for t in timestamps if t > window_start]
    if len(timestamps) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait before uploading again.")
    timestamps.append(now)


@router.post("/upload", response_model=UploadResponse)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: str = Form("default"),
    current_user: dict | None = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)
    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in {"txt", "md", "csv", "json", "pdf", "doc", "docx"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: txt, md, csv, json, pdf, doc, docx")

    db = get_db()
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    user_id = current_user["email"] if current_user else None

    await db.documents.insert_one({
        "id": doc_id,
        "user_id": user_id,
        "filename": file.filename,
        "size": len(content),
        "uploaded_at": now,
        "status": "uploading",
        "chunks": 0,
        "conversation_id": conversation_id,
        "text": "",
        "chunk_texts": [],
        "chunk_embeddings": [],
        "error": None,
    })

    from backend.utils.document_parser import parse_document
    try:
        await db.documents.update_one({"id": doc_id}, {"$set": {"status": "extracting"}})
        text = parse_document(content, file.filename or "")
    except Exception:
        await db.documents.update_one({"id": doc_id}, {"$set": {"status": "failed", "error": "parse_failed"}})
        raise HTTPException(status_code=400, detail="Failed to parse document. The file may be corrupted or in an unsupported format.")

    from ai.chunking import chunk_text
    await db.documents.update_one({"id": doc_id}, {"$set": {"status": "chunking"}})
    chunks = chunk_text(text)

    await db.documents.update_one({"id": doc_id}, {"$set": {"status": "embedding"}})

    from ai.embeddings import embed
    try:
        chunk_embeddings = [await embed(chunk) for chunk in chunks]
    except Exception:
        await db.documents.update_one({"id": doc_id}, {"$set": {"status": "failed", "error": "embed_failed"}})
        raise HTTPException(status_code=500, detail="Failed to generate embeddings. Please try again.")

    await db.documents.update_one(
        {"id": doc_id},
        {
            "$set": {
                "status": "ready",
                "chunks": len(chunks),
                "text": text,
                "chunk_texts": chunks,
                "chunk_embeddings": chunk_embeddings,
                "error": None,
            }
        },
    )

    await db.files.insert_one({
        "id": doc_id,
        "user_id": user_id,
        "filename": file.filename,
        "content": content,
        "uploaded_at": now,
    })

    await db.conversations.update_one(
        {"id": conversation_id},
        {
            "$setOnInsert": {
                "id": conversation_id,
                "user_id": user_id,
                "title": f"Upload: {file.filename}",
                "created_at": now,
            },
            "$push": {"document_ids": doc_id},
            "$set": {"updated_at": now},
        },
        upsert=True,
    )

    return UploadResponse(
        filename=file.filename or "unknown",
        chunks=len(chunks),
        conversation_id=conversation_id,
        document_id=doc_id,
    )