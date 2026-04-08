"""
RAG router — natural language expense queries.
POST /api/rag/query
"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import QueryRequest, QueryResponse
from services.rag_service import rag_service
from services.observability import obs_service
from config import settings

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def rag_query(body: QueryRequest, db: Session = Depends(get_db)):
    """
    Natural language query over stored expenses.
    Pipeline: query rewriting → Chroma semantic search → ranking/clustering → LLM answer.
    """
    start = time.perf_counter()
    answer, rewritten, sources, tokens_used = await rag_service.query(
        body.query, top_k=body.top_k or 5
    )
    latency_ms = (time.perf_counter() - start) * 1000

    # Log to observability
    obs_service.log_rag_query(
        run_id=None,
        query=body.query,
        rewritten=rewritten,
        answer=answer,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        model=settings.GPT_MODEL if not settings.demo_mode else "demo",
        sources_count=len(sources),
    )

    return QueryResponse(
        answer=answer,
        sources=sources[:5],
        rewritten=rewritten,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        run_id=None,
    )
