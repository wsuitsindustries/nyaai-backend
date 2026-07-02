import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form
from backend.models.schemas import UploadResponse
from backend.database import get_db

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), conversation_id: str = Form("default")):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")

    from ai.chunking import chunk_text
    chunks = chunk_text(text)

    # Save to MongoDB
    db = get_db()
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    await db.documents.insert_one({
        "id": doc_id,
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
        "filename": file.filename,
        "content": content,
        "uploaded_at": now,
    })

    # Save conversation reference
    await db.conversations.update_one(
        {"id": conversation_id},
        {
            "$setOnInsert": {
                "id": conversation_id,
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