from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import QueryRequest, QueryResponse
from app.services.query_engine import query_engine

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Stage 2: Cross-Document Natural Language Query Endpoint.
    Routes queries to:
    - Pure Python deterministic math computation for arithmetic (sums, counts, avgs)
    - Direct image visual inspection fallback for visual details
    - Structured Claude reasoning over extracted JSON documents
    """
    return await query_engine.process_query(db, request)
