from fastapi import APIRouter, Depends
from backend.models.schemas import SearchRequest, SearchResponse
from backend.services.document import all_chunks
from backend.middleware.auth import get_current_user

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, current_user: dict | None = Depends(get_current_user)):
    from ai.retrieval import retrieve_texts
    user_id = current_user["email"] if current_user else None
    chunks = await all_chunks(user_id)
    results = await retrieve_texts(req.query, chunks, top_k=req.top_k)
    return SearchResponse(results=results)
