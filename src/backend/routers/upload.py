import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
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


@router.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    conversation_id: str = Form("default"),
    current_user: dict | None = Depends(get_current_user),
):
    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in {"txt", "md", "csv", "json", "pdf", "doc", "docx"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: txt, md, csv, json, pdf, doc, docx")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")

    from ai.chunking import chunk_text
    chunks = chunk_text(text)

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
        "status": "ready",
        "chunks": len(chunks),
        "conversation_id": conversation_id,
        "text": text,
        "chunk_texts": chunks,
        "error": None,
    })

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
                "updated_at": now,
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
