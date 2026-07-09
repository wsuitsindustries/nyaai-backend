import json
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from backend.models.schemas import ChatRequest, ChatResponse, Source
from backend.database import get_db
from backend.services.document import get_document_chunks_with_embeddings
from backend.middleware.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

MESSAGE_MAX_LENGTH = 10000


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, current_user: dict | None = Depends(get_current_user)):
    if len(req.message) > MESSAGE_MAX_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MESSAGE_MAX_LENGTH} characters)")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_id = current_user["email"] if current_user else None

    try:
        chunks, chunk_embeddings = await get_document_chunks_with_embeddings(user_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Knowledge base is temporarily unavailable. Please try again.")

    from ai.rag import answer_with_rag

    try:
        answer, relevant = await answer_with_rag(
            req.message, chunks, chunk_embeddings=chunk_embeddings, use_llm=True
        )
    except Exception:
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable. Please try again.")

    source_lookup = {}
    try:
        async for doc in get_db().documents.find({"status": "ready", **({"user_id": user_id} if user_id else {})}, {"filename": 1, "chunk_texts": 1}):
            for chunk in doc.get("chunk_texts", []):
                source_lookup[chunk] = doc.get("filename", "Document")
    except Exception:
        pass

    sources = [
        Source(
            title=source_lookup.get(chunk, "Document"),
            snippet=chunk[:120],
        )
        for chunk in relevant
    ]

    db = get_db()
    now = datetime.now(timezone.utc)

    try:
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
            {"id": req.conversation_id, "user_id": user_id},
            {
                "$setOnInsert": {
                    "id": req.conversation_id,
                    "user_id": user_id,
                    "title": req.message[:60],
                    "created_at": now,
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
        )
    except Exception:
        logger.exception("Failed to persist chat messages")

    return ChatResponse(answer=answer, sources=sources)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, current_user: dict | None = Depends(get_current_user)):
    if len(req.message) > MESSAGE_MAX_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MESSAGE_MAX_LENGTH} characters)")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_id = current_user["email"] if current_user else None

    try:
        chunks, chunk_embeddings = await get_document_chunks_with_embeddings(user_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Knowledge base is temporarily unavailable.")

    from ai.rag import stream_rag

    db = get_db()
    now = datetime.now(timezone.utc)

    try:
        await db.messages.insert_one({
            "id": str(uuid.uuid4()),
            "conversation_id": req.conversation_id,
            "user_id": user_id,
            "role": "user",
            "content": req.message,
            "created_at": now,
        })
    except Exception:
        logger.exception("Failed to persist user message")

    source_lookup = {}
    try:
        async for doc in db.documents.find({"status": "ready", **({"user_id": user_id} if user_id else {})}, {"filename": 1, "chunk_texts": 1}):
            for chunk in doc.get("chunk_texts", []):
                source_lookup[chunk] = doc.get("filename", "Document")
    except Exception:
        pass

    assistant_msg_id = str(uuid.uuid4())

    async def event_stream():
        full_answer = ""
        try:
            async for token in stream_rag(req.message, chunks, chunk_embeddings=chunk_embeddings):
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:
            logger.exception("Stream error")
            yield f"data: {json.dumps({'error': 'AI service temporarily unavailable'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            return

        from ai.retrieval import retrieve_texts
        try:
            relevant = await retrieve_texts(req.message, chunks)
        except Exception:
            relevant = []

        sources = [
            Source(
                title=source_lookup.get(chunk, "Document"),
                snippet=chunk[:120],
            )
            for chunk in relevant
        ]

        yield f"data: {json.dumps({'done': True, 'sources': [s.model_dump() for s in sources]})}\n\n"

        try:
            await db.messages.insert_one({
                "id": assistant_msg_id,
                "conversation_id": req.conversation_id,
                "user_id": user_id,
                "role": "assistant",
                "content": full_answer,
                "sources": [s.model_dump() for s in sources],
                "created_at": now,
            })

            await db.conversations.update_one(
                {"id": req.conversation_id, "user_id": user_id},
                {
                    "$setOnInsert": {
                        "id": req.conversation_id,
                        "user_id": user_id,
                        "title": req.message[:60],
                        "created_at": now,
                    },
                    "$set": {"updated_at": now},
                },
                upsert=True,
            )
        except Exception:
            logger.exception("Failed to persist assistant response")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
