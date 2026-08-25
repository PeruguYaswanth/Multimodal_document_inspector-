import json
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PIL import Image, ImageDraw

from app.database import Base
from app.models import Document
from app.schemas import QueryRequest
from app.services.image_processor import ImageProcessor
from app.services.pipeline import pipeline
from app.services.query_engine import query_engine
from app.services.vision_client import vision_client

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.mark.asyncio
async def test_novel_food_unhinted_filename(db_session, tmp_path):
    """
    Test 1: Novel food dish with unhinted filename (IMG_2938.jpg).
    Verifies that classification and extraction depend on visual content, not filename.
    """
    img_path = tmp_path / "IMG_2938.jpg"
    img = Image.new("RGB", (600, 600), color="#2D3748")
    img.save(img_path)

    # Dynamic Claude vision mock response for this specific image content
    mock_classification = {
        "document_type": "culinary_photograph",
        "primary_subject": "Wild Alaskan Salmon with Charred Asparagus and Lemon Herb Butter",
        "key_fields": ["dish_name", "cuisine_type", "primary_ingredients", "plating_style", "estimated_prep_time"],
        "is_text_heavy": False,
        "is_data_heavy": False,
        "is_non_informational": False
    }
    mock_extraction = {
        "document_type": "culinary_photograph",
        "primary_subject": "Wild Alaskan Salmon with Charred Asparagus and Lemon Herb Butter",
        "summary": "A close-up gourmet plate featuring pan-seared wild Alaskan salmon served over roasted asparagus stalks garnished with fresh dill.",
        "extracted_fields": {
            "dish_name": "Wild Alaskan Salmon",
            "accompaniments": ["Charred Asparagus", "Lemon Wedges", "Dill Butter"],
            "cooking_method": "Pan-seared",
            "presentation": "Fine Dining Ceramic Plate"
        },
        "tables": [],
        "full_text": "",
        "confidence": "high",
        "low_confidence_notes": []
    }

    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_classification)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_extraction)):
        
        with open(img_path, "rb") as f:
            file_bytes = f.read()

        meta = ImageProcessor.process_and_save(file_bytes, img_path)
        doc, _ = await pipeline.process_image_two_stage(
            image_path=str(img_path),
            original_filename="IMG_2938.jpg",
            file_bytes=file_bytes,
            db=db_session,
            meta_info=meta
        )

        assert doc.document_type == "culinary_photograph"
        assert doc.primary_subject == "Wild Alaskan Salmon with Charred Asparagus and Lemon Herb Butter"
        assert doc.extracted_fields["dish_name"] == "Wild Alaskan Salmon"
        assert "curd" not in doc.primary_subject.lower()

    # Query with alternative phrasing: "what dish is shown here"
    with patch.object(vision_client, "generate_chat_answer", AsyncMock(return_value="The image depicts Wild Alaskan Salmon served with charred asparagus.")):
        req = QueryRequest(question="what dish is shown here", document_ids=[doc.id])
        resp = await query_engine.process_query(db_session, req)
        assert "Wild Alaskan Salmon" in resp.answer
        assert len(resp.sources) == 1
        assert resp.sources[0].primary_subject == doc.primary_subject

@pytest.mark.asyncio
async def test_novel_parking_ticket(db_session, tmp_path):
    """
    Test 2: A completely novel document type: Parking Violation Ticket.
    """
    img_path = tmp_path / "ticket_9021.png"
    img = Image.new("RGB", (400, 700), color="#FFFBEB")
    img.save(img_path)

    mock_classification = {
        "document_type": "parking_violation_ticket",
        "primary_subject": "Municipal Parking Citation #SF-88392",
        "key_fields": ["citation_number", "violation_code", "fine_amount", "issue_date", "vehicle_plate", "due_date"],
        "is_text_heavy": True,
        "is_data_heavy": True,
        "is_non_informational": False
    }
    mock_extraction = {
        "document_type": "parking_violation_ticket",
        "primary_subject": "Municipal Parking Citation #SF-88392",
        "summary": "Municipal citation issued for parking in an expired meter zone on Montgomery St.",
        "extracted_fields": {
            "citation_number": "SF-88392",
            "violation": "Expired Meter (Code 32-A)",
            "fine_amount": 75.00,
            "issue_date": "2026-08-22",
            "due_date": "2026-09-12",
            "vehicle_plate": "7XYZ899"
        },
        "tables": [],
        "full_text": "MUNICIPAL PARKING AUTHORITY\nCITATION: SF-88392\nFINE: $75.00\nVEHICLE: 7XYZ899",
        "confidence": "high",
        "low_confidence_notes": []
    }

    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_classification)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_extraction)):
        
        with open(img_path, "rb") as f:
            file_bytes = f.read()

        meta = ImageProcessor.process_and_save(file_bytes, img_path)
        doc, _ = await pipeline.process_image_two_stage(
            image_path=str(img_path),
            original_filename="ticket_9021.png",
            file_bytes=file_bytes,
            db=db_session,
            meta_info=meta
        )

        assert doc.document_type == "parking_violation_ticket"
        assert doc.extracted_fields["fine_amount"] == 75.00
        assert doc.extracted_fields["citation_number"] == "SF-88392"

@pytest.mark.asyncio
async def test_cross_document_multi_type_synthesis(db_session):
    """
    Test 4: Synthesizing information across 2+ completely different document types.
    """
    # Doc 1: Receipt ($18.50)
    d1 = Document(
        image_path="/path/receipt.png",
        original_filename="receipt.png",
        document_type="receipt",
        primary_subject="Coffee Shop Receipt",
        summary="Purchase of coffee and pastry",
        extracted_fields={"total_amount": 18.50, "merchant": "Blue Bottle"},
        full_text="Total $18.50",
        confidence="high",
        content_hash="h1"
    )
    # Doc 2: Parking Ticket ($75.00)
    d2 = Document(
        image_path="/path/ticket.png",
        original_filename="ticket.png",
        document_type="parking_violation_ticket",
        primary_subject="Parking Citation",
        summary="Parking violation citation",
        extracted_fields={"fine_amount": 75.00, "citation_number": "SF-88392"},
        full_text="Citation SF-88392 Fine $75.00",
        confidence="high",
        content_hash="h2"
    )
    db_session.add_all([d1, d2])
    db_session.commit()

    # Query asking total expenses across both unrelated documents
    req = QueryRequest(question="How much are all my combined expenses and fines total?")
    with patch.object(vision_client, "generate_chat_answer", AsyncMock(return_value="Your total combined expenses and citations amount to $93.50 ($18.50 receipt + $75.00 fine).")):
        resp = await query_engine.process_query(db_session, req)
        assert resp.computation is not None
        assert resp.computation.result == 93.50  # 18.50 + 75.00 computed in code
        assert len(resp.sources) == 2

@pytest.mark.asyncio
async def test_ambiguous_low_quality_image(db_session, tmp_path):
    """
    Test 5: Low-quality/blurry image correctly flags low confidence.
    """
    img_path = tmp_path / "blurry_snap.jpg"
    img = Image.new("RGB", (300, 300), color="#555555")
    img.save(img_path)

    mock_classification = {
        "document_type": "unclear_document",
        "primary_subject": "Degraded printed document",
        "key_fields": ["header", "fragmentary_text"],
        "is_text_heavy": True,
        "is_data_heavy": False,
        "is_non_informational": False
    }
    mock_extraction = {
        "document_type": "unclear_document",
        "primary_subject": "Degraded printed document",
        "summary": "Severe motion blur and low resolution prevent clear character identification.",
        "extracted_fields": {
            "header": None,
            "fragmentary_text": "partial legible fragment '...REQ...'"
        },
        "tables": [],
        "full_text": "...REQ...",
        "confidence": "low",
        "low_confidence_notes": ["Image resolution too low", "Severe blur preventing confident OCR"]
    }

    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_classification)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_extraction)):
        
        with open(img_path, "rb") as f:
            file_bytes = f.read()

        meta = ImageProcessor.process_and_save(file_bytes, img_path)
        doc, _ = await pipeline.process_image_two_stage(
            image_path=str(img_path),
            original_filename="blurry_snap.jpg",
            file_bytes=file_bytes,
            db=db_session,
            meta_info=meta
        )

        assert doc.confidence == "low"
        assert len(doc.low_confidence_notes) == 2
        assert doc.is_reviewed is False  # Auto-flagged for manual review

@pytest.mark.asyncio
async def test_no_regression_curd_rice(db_session, tmp_path):
    """
    Test 6 (Regression verification): 'curd-rice.jpg' passes through the SAME general pipeline.
    """
    img_path = tmp_path / "curd-rice.jpg"
    img = Image.new("RGB", (600, 600), color="#E2E8F0")
    img.save(img_path)

    mock_classification = {
        "document_type": "food_dish",
        "primary_subject": "South Indian Curd Rice (Thayir Sadam) with Mustard Seed Tempering",
        "key_fields": ["dish_name", "regional_cuisine", "key_garnishes", "texture_description"],
        "is_text_heavy": False,
        "is_data_heavy": False,
        "is_non_informational": False
    }
    mock_extraction = {
        "document_type": "food_dish",
        "primary_subject": "South Indian Curd Rice (Thayir Sadam) with Mustard Seed Tempering",
        "summary": "A bowl of traditional South Indian Curd Rice seasoned with mustard seeds, curry leaves, and green chillies.",
        "extracted_fields": {
            "dish_name": "Curd Rice (Thayir Sadam)",
            "cuisine": "South Indian",
            "temperings": ["Mustard Seeds", "Curry Leaves", "Ginger", "Green Chillies"],
            "dairy_base": "Yogurt / Curd"
        },
        "tables": [],
        "full_text": "",
        "confidence": "high",
        "low_confidence_notes": []
    }

    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_classification)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_extraction)):
        
        with open(img_path, "rb") as f:
            file_bytes = f.read()

        meta = ImageProcessor.process_and_save(file_bytes, img_path)
        doc, _ = await pipeline.process_image_two_stage(
            image_path=str(img_path),
            original_filename="curd-rice.jpg",
            file_bytes=file_bytes,
            db=db_session,
            meta_info=meta
        )

        assert doc.document_type == "food_dish"
        assert doc.primary_subject == "South Indian Curd Rice (Thayir Sadam) with Mustard Seed Tempering"
        assert doc.extracted_fields["dish_name"] == "Curd Rice (Thayir Sadam)"
        assert "Analyzed document document" not in doc.summary

    # Query about the food item
    with patch.object(vision_client, "generate_chat_answer", AsyncMock(return_value="The food item shown in the image is South Indian Curd Rice (Thayir Sadam), garnished with mustard seeds and curry leaves.")):
        req = QueryRequest(question="what is the name of the food item from the selected image", document_ids=[doc.id])
        resp = await query_engine.process_query(db_session, req)
        assert "Curd Rice" in resp.answer
        assert "relevant details matching your inquiry" not in resp.answer
