from fastapi import APIRouter, HTTPException, Depends
from backend.models.schemas import DocumentListResponse, DocumentResponse, DocumentStatusResponse
from backend.database import get_db
from backend.middleware.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(current_user: dict | None = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["email"] if current_user else None
    if user_id is None:
        return DocumentListResponse(documents=[])
    filter_query = {"user_id": user_id}
    cursor = db.documents.find(filter_query, {"text": 0, "chunk_texts": 0}).sort("uploaded_at", -1)
    docs = []
    async for doc in cursor:
        docs.append(DocumentResponse(
            id=doc["id"],
            filename=doc["filename"],
            size=doc["size"],
            uploaded_at=doc["uploaded_at"],
            status=doc.get("status", "ready"),
            chunks=doc.get("chunks", 0),
            error=None,
        ))
    return DocumentListResponse(documents=docs)


@router.get("/documents/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(doc_id: str, current_user: dict | None = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["email"] if current_user else None
    doc = await db.documents.find_one({"id": doc_id, **({"user_id": user_id} if user_id else {})}, {"status": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(id=doc_id, status=doc.get("status", "ready"))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: dict | None = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["email"] if current_user else None
    doc = await db.documents.find_one({"id": doc_id, **({"user_id": user_id} if user_id else {})}, {"id": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.documents.delete_one({"id": doc_id, **({"user_id": user_id} if user_id else {})})
    await db.files.delete_one({"id": doc_id})
    return {"ok": True}


@router.post("/documents/{doc_id}/reindex", response_model=DocumentStatusResponse)
async def reindex_document(doc_id: str, current_user: dict | None = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["email"] if current_user else None
    doc = await db.documents.find_one({"id": doc_id, **({"user_id": user_id} if user_id else {})})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_doc = await db.files.find_one({"id": doc_id, "user_id": user_id}) if user_id else None
    if file_doc and "content" in file_doc:
        from backend.utils.document_parser import parse_document
        try:
            text = parse_document(file_doc["content"], doc.get("filename", ""))
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to parse document. The file may be corrupted or in an unsupported format.")
    else:
        text = doc.get("text", "")

    from ai.chunking import chunk_text
    chunks = chunk_text(text)

    from ai.embeddings import embed
    try:
        chunk_embeddings = [await embed(chunk) for chunk in chunks]
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate embeddings. Please try again.")

    await db.documents.update_one(
        {"id": doc_id},
        {"$set": {"status": "ready", "chunks": len(chunks), "text": text, "chunk_texts": chunks, "chunk_embeddings": chunk_embeddings}},
    )
    return DocumentStatusResponse(id=doc_id, status="ready")
