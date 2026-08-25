from datetime import datetime
from typing import Dict, Any, List, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

# --- Stage 1A: Classification Schema (Fully Dynamic) ---
class ClassificationResult(BaseModel):
    document_type: str = Field(..., description="Detected document or image category determined entirely by image content")
    primary_subject: Optional[str] = Field(None, description="Primary subject or entity in the image (e.g., Curd Rice dish, Parking Violation, Blood Test Report)")
    key_fields: List[str] = Field(default_factory=list, description="The 5-10 most important salient fields to extract from this specific image")
    is_text_heavy: bool = Field(default=False, description="Whether image is predominantly text")
    is_data_heavy: bool = Field(default=False, description="Whether image contains tabular, numeric, or dense structured data")
    is_non_informational: bool = Field(default=False, description="True if the image contains no meaningful text or identifiable structured subjects")
    notes: Optional[str] = None

# --- Stage 1B: Dynamic Extraction Schema ---
class TableData(BaseModel):
    title: Optional[str] = "Table"
    rows: List[Dict[str, Any]] = Field(default_factory=list)

class DynamicExtractionResult(BaseModel):
    document_type: str
    primary_subject: Optional[str] = None
    currency: Optional[str] = Field(None, description="Detected currency symbol (e.g. ₹, $, €, £) or code (INR, USD, EUR)")
    summary: str = Field(..., description="1-2 sentence concise grounded description of what is in the image")
    extracted_fields: Dict[str, Any] = Field(default_factory=dict, description="Dynamic key-value pairs specific to this image")
    tables: List[TableData] = Field(default_factory=list)
    full_text: str = Field(default="", description="All readable text, transcribed accurately as-is")
    confidence: Literal["high", "medium", "low"] = "medium"
    low_confidence_notes: List[str] = Field(default_factory=list)

# --- Document API Schemas ---
class DocumentResponse(BaseModel):
    id: int
    image_path: str
    original_filename: str
    uploaded_at: Optional[datetime] = None
    document_type: str
    primary_subject: Optional[str] = None
    currency: Optional[str] = None
    summary: Optional[str] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    full_text: str = ""
    confidence: str = "medium"
    low_confidence_notes: List[str] = Field(default_factory=list)
    content_hash: str
    is_text_heavy: bool = False
    is_data_heavy: bool = False
    is_reviewed: bool = False
    is_non_informational: bool = False
    meta_info: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

class DocumentUpdateRequest(BaseModel):
    document_type: Optional[str] = None
    primary_subject: Optional[str] = None
    currency: Optional[str] = None
    summary: Optional[str] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    full_text: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None
    is_reviewed: Optional[bool] = None
    low_confidence_notes: Optional[List[str]] = None

# --- Stage 2: Dynamic Query Schemas ---
class QueryRequest(BaseModel):
    question: str
    document_ids: Optional[List[int]] = None
    scope: Literal["all", "selected", "single"] = "all"
    force_vision: bool = False

class CitationSource(BaseModel):
    document_id: int
    filename: str
    document_type: str
    primary_subject: Optional[str] = None
    currency: Optional[str] = None
    matched_snippet: Optional[str] = None
    matched_fields: Optional[Dict[str, Any]] = None

class ComputationDetails(BaseModel):
    operation: str
    target_field: str
    raw_values: List[float] = Field(default_factory=list)
    result: Union[float, int, str]
    currency: Optional[str] = None
    explanation: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    query_type: Literal["structured_reasoning", "code_computation", "visual_inspection", "general_search", "error"]
    sources: List[CitationSource] = Field(default_factory=list)
    computation: Optional[ComputationDetails] = None
    visual_inspection_used: bool = False
    suggested_followups: List[str] = Field(default_factory=list)

# --- Collection Stats Schema ---
class CollectionStats(BaseModel):
    total_documents: int
    reviewed_count: int
    needs_review_count: int
    low_confidence_count: int
    type_breakdown: Dict[str, int]
    confidence_breakdown: Dict[str, int]
