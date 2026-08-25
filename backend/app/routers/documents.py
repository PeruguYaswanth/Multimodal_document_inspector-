import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

import logging
from app.database import get_db
from app.config import settings
from app.models import Document
from app.schemas import DocumentResponse, DocumentUpdateRequest, CollectionStats
from app.services.image_processor import ImageProcessor
from app.services.pipeline import pipeline
from app.services.vision_client import (
    AIServiceUnavailableError,
    AuthenticationError,
    ModelNotFoundError
)

logger = logging.getLogger("documents_router")
router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=List[DocumentResponse])
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Stage 1 Entry: Multimodal Ingestion Pipeline.
    Uploads 1 to N images, runs dynamic 2-stage vision analysis, saves records.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    results = []
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )

        file_bytes = await file.read()
        if len(file_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )

        # Unique save path
        unique_name = f"{uuid.uuid4().hex}_{Path(file.filename).stem}{ext}"
        destination = settings.UPLOAD_DIR / unique_name
        
        # Process and save with EXIF orientation correction
        meta = ImageProcessor.process_and_save(file_bytes, destination)

        try:
            doc, is_dup = await pipeline.process_image_two_stage(
                image_path=meta["saved_path"],
                original_filename=file.filename,
                file_bytes=file_bytes,
                db=db,
                meta_info=meta
            )
            results.append(doc)
        except HTTPException:
            raise
        except (AIServiceUnavailableError, Exception) as e:
            if isinstance(e, AuthenticationError):
                logger.error(f"Hugging Face auth failure on upload: {e}")
                raise HTTPException(status_code=401, detail="Hugging Face authentication failed.")
            if isinstance(e, ModelNotFoundError):
                logger.error(f"Hugging Face model not found on upload: {e}")
                raise HTTPException(status_code=404, detail="Hugging Face model is unavailable.")
            
            err_str = str(e).lower()
            if isinstance(e, AIServiceUnavailableError) or any(term in err_str for term in ["503", "502", "504", "429", "unavailable", "overloaded", "temporarily busy", "aiserviceunavailable"]):
                logger.error(f"Hugging Face API 503/429 unavailable on upload: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="The AI service is temporarily busy. Please try again in a few seconds."
                )
            logger.error(f"Upload processing failed for {file.filename}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")

    return results

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    document_type: Optional[str] = None,
    confidence: Optional[str] = None,
    needs_review: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Document)
    
    if document_type:
        query = query.filter(Document.document_type.ilike(f"%{document_type}%"))
    if confidence:
        query = query.filter(Document.confidence == confidence)
    if needs_review is not None:
        if needs_review:
            query = query.filter(Document.is_reviewed == False)
        else:
            query = query.filter(Document.is_reviewed == True)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Document.original_filename.ilike(term),
                Document.document_type.ilike(term),
                Document.summary.ilike(term),
                Document.full_text.ilike(term)
            )
        )
        
    return query.order_by(desc(Document.uploaded_at)).all()

@router.get("/stats/summary", response_model=CollectionStats)
def get_stats(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    total = len(docs)
    reviewed = sum(1 for d in docs if d.is_reviewed)
    needs_rev = sum(1 for d in docs if not d.is_reviewed)
    low_conf = sum(1 for d in docs if d.confidence == "low")
    
    type_counts = {}
    conf_counts = {"high": 0, "medium": 0, "low": 0}
    for d in docs:
        t = d.document_type or "unclassified"
        type_counts[t] = type_counts.get(t, 0) + 1
        conf = d.confidence or "medium"
        conf_counts[conf] = conf_counts.get(conf, 0) + 1

    return CollectionStats(
        total_documents=total,
        reviewed_count=reviewed,
        needs_review_count=needs_rev,
        low_confidence_count=low_conf,
        type_breakdown=type_counts,
        confidence_breakdown=conf_counts
    )

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Review fetch failed for document {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch document for review: {str(e)}")

@router.patch("/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: int,
    payload: DocumentUpdateRequest,
    db: Session = Depends(get_db)
):
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        if payload.document_type is not None:
            doc.document_type = payload.document_type
        if payload.primary_subject is not None:
            doc.primary_subject = payload.primary_subject
        if payload.currency is not None:
            doc.currency = payload.currency
        if payload.summary is not None:
            doc.summary = payload.summary
        if payload.extracted_fields is not None:
            doc.extracted_fields = payload.extracted_fields
        if payload.tables is not None:
            doc.tables = payload.tables
        if payload.full_text is not None:
            doc.full_text = payload.full_text
        if payload.confidence is not None:
            doc.confidence = payload.confidence
        if payload.is_reviewed is not None:
            doc.is_reviewed = payload.is_reviewed
        if payload.low_confidence_notes is not None:
            doc.low_confidence_notes = payload.low_confidence_notes

        db.commit()
        db.refresh(doc)
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Review update failed for document {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save document review changes: {str(e)}")

@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Delete image file if exists
    if os.path.exists(doc.image_path):
        try:
            os.remove(doc.image_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()
    return {"status": "deleted", "id": doc_id}

@router.post("/{doc_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc or not os.path.exists(doc.image_path):
        raise HTTPException(status_code=404, detail="Document or image file not found")

    logger.info(f"[REPROCESS] Explicitly reprocessing document #{doc_id} ({doc.original_filename})...")

    with open(doc.image_path, "rb") as f:
        file_bytes = f.read()

    # Re-run pipeline with graceful 503 handling and force reprocessing
    try:
        reprocessed, _ = await pipeline.process_image_two_stage(
            image_path=doc.image_path,
            original_filename=doc.original_filename,
            file_bytes=file_bytes,
            db=db,
            meta_info=doc.meta_info,
            force_reprocess=True,
            existing_doc_id=doc_id
        )
        return reprocessed
    except HTTPException:
        raise
    except (AIServiceUnavailableError, Exception) as e:
        if isinstance(e, AuthenticationError):
            logger.error(f"Hugging Face auth failure on reprocess: {e}")
            raise HTTPException(status_code=401, detail=f"Hugging Face authentication failed: {str(e)}")
        if isinstance(e, ModelNotFoundError):
            logger.error(f"Hugging Face model not found on reprocess: {e}")
            raise HTTPException(status_code=404, detail=f"Hugging Face model is unavailable: {str(e)}")

        err_str = str(e).lower()
        if isinstance(e, AIServiceUnavailableError) or any(term in err_str for term in ["503", "502", "504", "429", "unavailable", "overloaded", "temporarily busy", "aiserviceunavailable"]):
            logger.error(f"Hugging Face API 503/429 unavailable on reprocess: {e}")
            raise HTTPException(
                status_code=503,
                detail="The AI service is temporarily busy. Please try again in a few seconds."
            )
        logger.error(f"Reprocessing failed for document {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")
