from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(512), nullable=False)
    original_filename = Column(String(256), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    
    # Fully dynamic classification & subject
    document_type = Column(String(64), nullable=False, default="unclassified", index=True)
    primary_subject = Column(String(128), nullable=True, default=None, index=True)
    currency = Column(String(16), nullable=True, default=None)  # e.g., ₹, $, €, £, INR, USD
    summary = Column(Text, nullable=True)
    
    # Universal flexible fields (arbitrary key-values per document)
    extracted_fields = Column(JSON, default=dict, nullable=False)
    tables = Column(JSON, default=list, nullable=False)
    full_text = Column(Text, default="", nullable=False, index=True)
    
    # Quality & Confidence
    confidence = Column(String(16), default="medium", index=True)  # high, medium, low
    low_confidence_notes = Column(JSON, default=list, nullable=False)
    
    # Dedup & Flags
    content_hash = Column(String(64), nullable=False, index=True)
    is_text_heavy = Column(Boolean, default=False)
    is_data_heavy = Column(Boolean, default=False)
    is_reviewed = Column(Boolean, default=False, index=True)
    is_non_informational = Column(Boolean, default=False)
    
    # Metadata (dimensions, size, format, exif)
    meta_info = Column(JSON, default=dict, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "image_path": self.image_path,
            "original_filename": self.original_filename,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "document_type": self.document_type,
            "primary_subject": self.primary_subject,
            "currency": self.currency,
            "summary": self.summary,
            "extracted_fields": self.extracted_fields or {},
            "tables": self.tables or [],
            "full_text": self.full_text or "",
            "confidence": self.confidence,
            "low_confidence_notes": self.low_confidence_notes or [],
            "content_hash": self.content_hash,
            "is_text_heavy": self.is_text_heavy,
            "is_data_heavy": self.is_data_heavy,
            "is_reviewed": self.is_reviewed,
            "is_non_informational": self.is_non_informational,
            "meta_info": self.meta_info or {},
        }
