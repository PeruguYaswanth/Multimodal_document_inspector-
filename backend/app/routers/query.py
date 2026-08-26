import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import QueryRequest, QueryResponse
from app.services.query_engine import query_engine
from app.services.vision_client import (
    AIServiceUnavailableError,
    AuthenticationError,
    ModelNotFoundError
)

logger = logging.getLogger("query_router")
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
    - Structured OpenRouter / OpenAI Multimodal reasoning over extracted JSON documents
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=422, detail="Question field cannot be empty.")

    try:
        logger.info(f"Processing query: '{request.question}' (scope={request.scope}, document_ids={request.document_ids})")
        return await query_engine.process_query(db, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error processing query '{request.question}': {e}", exc_info=True)
        if isinstance(e, AuthenticationError):
            logger.error(f"[LLM] OpenRouter authentication failed: {e}")
            raise HTTPException(
                status_code=401,
                detail=f"OpenRouter authentication failed: {str(e)}"
            )
        if isinstance(e, ModelNotFoundError):
            logger.error(f"[LLM] OpenRouter model not found: {e}")
            raise HTTPException(
                status_code=404,
                detail=f"OpenRouter model is unavailable: {str(e)}"
            )
        err_str = str(e).lower()
        if any(term in err_str for term in ["503", "502", "504", "429", "unavailable", "overloaded", "aiserviceunavailable"]):
            raise HTTPException(
                status_code=503,
                detail="The AI service is temporarily busy. Please try again in a few seconds."
            )
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")
