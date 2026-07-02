from fastapi import APIRouter
from backend.models.schemas import SearchRequest, SearchResponse
from backend.services.document import get_document_chunks, all_chunks

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    from ai.retrieval import retrieve
    chunks = await all_chunks()
    results = retrieve(req.query, chunks, top_k=req.top_k)
    return SearchResponse(results=results)