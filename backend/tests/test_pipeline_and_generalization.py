import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PIL import Image

from app.database import Base
from app.models import Document
from app.services.image_processor import ImageProcessor
from app.services.pipeline import pipeline
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
async def test_stage1_generalization_across_document_types(db_session, tmp_path):
    """
    Verifies that the Two-Stage Pipeline successfully ingests and generalizes across
    multiple distinct document types without any hardcoded branch.
    """
    categories = [
        ("coffee_receipt.png", "receipt", "Coffee Shop Receipt", {"total_amount": 18.50, "merchant": "Blue Bottle"}, "#E2E8F0"),
        ("architecture_notes.png", "handwritten_note", "Project Architecture Notes", {"topic": "Vision System", "priority": "High"}, "#FEF3C7"),
        ("business_card.png", "business_card", "Executive Card", {"person_name": "Dr. Evelyn Vance", "email": "evelyn@ai.com"}, "#0F172A"),
    ]

    for fname, dtype, subject, fields, col in categories:
        img_path = tmp_path / fname
        Image.new("RGB", (300, 300), color=col).save(img_path)

        mock_classify = {
            "document_type": dtype,
            "primary_subject": subject,
            "key_fields": list(fields.keys()),
            "is_text_heavy": True,
            "is_data_heavy": False,
            "is_non_informational": False
        }
        mock_extract = {
            "document_type": dtype,
            "primary_subject": subject,
            "summary": f"Structured extraction of {subject}.",
            "extracted_fields": fields,
            "tables": [],
            "full_text": f"Scanned text of {subject}",
            "confidence": "high",
            "low_confidence_notes": []
        }

        with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_classify)), \
             patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_extract)):

            with open(img_path, "rb") as f:
                file_bytes = f.read()

            meta = ImageProcessor.process_and_save(file_bytes, img_path)
            doc, is_dup = await pipeline.process_image_two_stage(
                image_path=str(img_path),
                original_filename=fname,
                file_bytes=file_bytes,
                db=db_session,
                meta_info=meta
            )

            assert doc.id is not None
            assert not is_dup
            assert doc.document_type == dtype
            assert doc.primary_subject == subject
            assert isinstance(doc.extracted_fields, dict)

@pytest.mark.asyncio
async def test_content_hash_deduplication(db_session, tmp_path):
    img_path = tmp_path / "test_dup.png"
    Image.new("RGB", (100, 100), color="#AABBCC").save(img_path)

    with open(img_path, "rb") as f:
        file_bytes = f.read()

    meta = ImageProcessor.process_and_save(file_bytes, img_path)
    mock_classify = {
        "document_type": "diagram",
        "primary_subject": "System Topology",
        "key_fields": ["nodes"],
        "is_text_heavy": False,
        "is_data_heavy": False,
        "is_non_informational": False
    }
    mock_extract = {
        "document_type": "diagram",
        "primary_subject": "System Topology",
        "summary": "Topology overview",
        "extracted_fields": {"nodes": ["A", "B"]},
        "tables": [],
        "full_text": "",
        "confidence": "high",
        "low_confidence_notes": []
    }

    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_classify)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_extract)):

        doc1, is_dup1 = await pipeline.process_image_two_stage(
            image_path=str(img_path),
            original_filename="test_dup.png",
            file_bytes=file_bytes,
            db=db_session,
            meta_info=meta
        )
        assert is_dup1 is False

        doc2, is_dup2 = await pipeline.process_image_two_stage(
            image_path=str(img_path),
            original_filename="test_dup.png",
            file_bytes=file_bytes,
            db=db_session,
            meta_info=meta
        )
        assert is_dup2 is True
        assert doc1.id == doc2.id
