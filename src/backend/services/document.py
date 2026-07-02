from backend.database import get_db


async def get_document_chunks() -> list[str]:
    db = get_db()
    cursor = db.documents.find({"status": "ready"}, {"chunk_texts": 1})
    chunks = []
    async for doc in cursor:
        chunks.extend(doc.get("chunk_texts", []))
    return chunks


async def all_chunks() -> list[str]:
    return await get_document_chunks()