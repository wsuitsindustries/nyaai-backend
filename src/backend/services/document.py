from backend.database import get_db


def _build_filter(user_id: str | None = None) -> dict:
    if user_id is None:
        return {"_id": None}
    return {"status": "ready", "user_id": user_id}


async def get_document_chunks(user_id: str | None = None) -> list[str]:
    db = get_db()
    cursor = db.documents.find(_build_filter(user_id), {"chunk_texts": 1})
    chunks = []
    async for doc in cursor:
        chunks.extend(doc.get("chunk_texts", []))
    return chunks


async def get_document_chunks_with_sources(user_id: str | None = None) -> list[dict]:
    db = get_db()
    cursor = db.documents.find(_build_filter(user_id), {"filename": 1, "chunk_texts": 1})
    items = []
    async for doc in cursor:
        for chunk in doc.get("chunk_texts", []):
            items.append({"text": chunk, "filename": doc.get("filename", "Unknown")})
    return items


async def get_document_chunks_with_embeddings(user_id: str | None = None) -> tuple[list[str], list[list[float]] | None]:
    db = get_db()
    cursor = db.documents.find(_build_filter(user_id), {"chunk_texts": 1, "chunk_embeddings": 1})
    chunks = []
    embeddings = []
    has_embeddings = True
    async for doc in cursor:
        texts = doc.get("chunk_texts", [])
        embs = doc.get("chunk_embeddings", [])
        chunks.extend(texts)
        if embs and len(embs) == len(texts):
            embeddings.extend(embs)
        else:
            has_embeddings = False
    return chunks, embeddings if has_embeddings else None


async def all_chunks(user_id: str | None = None) -> list[str]:
    return await get_document_chunks(user_id)