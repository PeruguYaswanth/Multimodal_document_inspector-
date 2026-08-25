import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Document
from app.schemas import QueryRequest
from app.services.query_engine import query_engine
from app.services.vision_client import vision_client

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture
def populated_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    
    doc1 = Document(
        image_path="/dummy/receipt1.png",
        original_filename="receipt_coffee.png",
        document_type="receipt",
        primary_subject="Blue Bottle Coffee Receipt",
        summary="Coffee shop purchase receipt",
        extracted_fields={"total_amount": 18.50, "merchant_name": "Blue Bottle", "currency": "USD"},
        tables=[],
        full_text="Blue Bottle Coffee Total: $18.50",
        confidence="high",
        low_confidence_notes=[],
        content_hash="hash_001",
        is_reviewed=True
    )
    doc2 = Document(
        image_path="/dummy/receipt2.png",
        original_filename="receipt_dinner.png",
        document_type="receipt",
        primary_subject="Trattoria Dinner Receipt",
        summary="Restaurant dinner receipt",
        extracted_fields={"total_amount": 42.00, "merchant_name": "Trattoria Della Nonna", "currency": "USD"},
        tables=[],
        full_text="Trattoria Della Nonna Total: $42.00",
        confidence="high",
        low_confidence_notes=[],
        content_hash="hash_002",
        is_reviewed=True
    )
    doc3 = Document(
        image_path="/dummy/card.png",
        original_filename="business_card.png",
        document_type="business_card",
        primary_subject="Dr. Evelyn Vance Business Card",
        summary="AI researcher business card",
        extracted_fields={"person_name": "Dr. Evelyn Vance", "email": "evelyn@neuraltech.ai"},
        tables=[],
        full_text="Dr. Evelyn Vance VP of AI Systems email: evelyn@neuraltech.ai",
        confidence="high",
        low_confidence_notes=[],
        content_hash="hash_003",
        is_reviewed=True
    )

    db.add_all([doc1, doc2, doc3])
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.mark.asyncio
async def test_zero_hallucination_math_in_python(populated_db):
    req = QueryRequest(question="How much did I spend total across all receipts?")
    with patch.object(vision_client, "generate_chat_answer", AsyncMock(return_value="You spent a total of $60.50 across your 2 receipts.")):
        response = await query_engine.process_query(populated_db, req)
        assert response.computation is not None
        assert response.computation.operation == "sum"
        assert response.computation.result == 60.50
        assert len(response.computation.raw_values) == 2

@pytest.mark.asyncio
async def test_average_and_count_math(populated_db):
    req_avg = QueryRequest(question="What was the average amount spent?")
    with patch.object(vision_client, "generate_chat_answer", AsyncMock(return_value="The average expense was $30.25.")):
        resp_avg = await query_engine.process_query(populated_db, req_avg)
        assert resp_avg.computation.operation == "average"
        assert resp_avg.computation.result == 30.25

@pytest.mark.asyncio
async def test_stored_context_query_routing(populated_db):
    req = QueryRequest(question="What does the dish shown in the photo look like?", force_vision=True)
    with patch.object(vision_client, "generate_chat_answer", AsyncMock(return_value="The photo displays a white porcelain bowl containing rice topped with mustard seeds and curry leaves.")) as mock_chat:
        resp = await query_engine.process_query(populated_db, req)
        assert resp.query_type == "structured_reasoning"
        assert resp.visual_inspection_used is False
        assert "porcelain bowl" in resp.answer
        mock_chat.assert_called_once()
