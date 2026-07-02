from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentStatus,
)
from backend.database import get_db

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    db = get_db()
    cursor = db.documents.find(
        {},
        {"text": 0, "chunk_texts": 0},
    ).sort("uploaded_at", -1)
    docs = []
    async for doc in cursor:
        docs.append(DocumentResponse(
            id=doc["id"],
            filename=doc["filename"],
            size=doc["size"],
            uploaded_at=doc["uploaded_at"],
            status=doc.get("status", "ready"),
            chunks=doc.get("chunks", 0),
            error=doc.get("error"),
        ))
    return DocumentListResponse(documents=docs)


@router.get("/documents/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(doc_id: str):
    db = get_db()
    doc = await db.documents.find_one({"id": doc_id}, {"status": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(id=doc_id, status=doc.get("status", "ready"))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    db = get_db()
    result = await db.documents.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.files.delete_one({"id": doc_id})
    return {"ok": True}


@router.post("/documents/{doc_id}/reindex", response_model=DocumentStatusResponse)
async def reindex_document(doc_id: str):
    db = get_db()
    doc = await db.documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    text = doc.get("text", "")
    from ai.chunking import chunk_text
    chunks = chunk_text(text)

    await db.documents.update_one(
        {"id": doc_id},
        {"$set": {
            "status": "ready",
            "chunks": len(chunks),
            "chunk_texts": chunks,
        }},
    )
    return DocumentStatusResponse(id=doc_id, status="ready")