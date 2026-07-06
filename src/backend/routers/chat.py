import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from backend.models.schemas import ChatRequest, ChatResponse, Source
from backend.database import get_db
from backend.services.document import get_document_chunks_with_sources
from backend.middleware.auth import get_current_user

router = APIRouter()


MESSAGE_MAX_LENGTH = 10000


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, current_user: dict | None = Depends(get_current_user)):
    if len(req.message) > MESSAGE_MAX_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MESSAGE_MAX_LENGTH} characters)")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    items = await get_document_chunks_with_sources()
    chunks = [item["text"] for item in items]
    source_lookup = {item["text"]: item["filename"] for item in items}

    from ai.rag import answer_with_rag

    answer, relevant = await answer_with_rag(req.message, chunks, use_llm=True)

    sources = [
        Source(
            title=source_lookup.get(chunk, "Document"),
            snippet=chunk[:120],
        )
        for chunk in relevant
    ]

    db = get_db()
    now = datetime.now(timezone.utc)
    user_id = current_user["email"] if current_user else None

    await db.messages.insert_one({
        "id": str(uuid.uuid4()),
        "conversation_id": req.conversation_id,
        "user_id": user_id,
        "role": "user",
        "content": req.message,
        "created_at": now,
    })

    msg_id = str(uuid.uuid4())
    await db.messages.insert_one({
        "id": msg_id,
        "conversation_id": req.conversation_id,
        "user_id": user_id,
        "role": "assistant",
        "content": answer,
        "sources": [s.model_dump() for s in sources],
        "created_at": now,
    })

    await db.conversations.update_one(
        {"id": req.conversation_id},
        {
            "$setOnInsert": {
                "id": req.conversation_id,
                "user_id": user_id,
                "title": req.message[:60],
                "created_at": now,
                "updated_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
    )

    return ChatResponse(answer=answer, sources=sources)
