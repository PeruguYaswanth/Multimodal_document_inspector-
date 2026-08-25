import pytest
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.services.vision_client import vision_client
from app.services.image_processor import ImageProcessor

client = TestClient(app)

@pytest.mark.asyncio
async def test_certificate_document_review_and_edit():
    """
    Verifies that a certificate / academic record with arbitrary dynamic fields
    (candidate_name, roll_number, degree, institution, gpa, marks) loads and reviews cleanly.
    """
    cert_path = Path("backend/uploads/academic_transcript.png")
    Image.new("RGB", (600, 800), "#F8FAFC").save(cert_path)

    mock_c = {
        "document_type": "academic_certificate",
        "primary_subject": "Bachelor of Technology Degree Certificate",
        "key_fields": ["candidate_name", "roll_number", "degree_title", "institution", "cgpa", "issue_date"],
        "is_text_heavy": True,
        "is_data_heavy": True,
        "is_non_informational": False
    }
    mock_e = {
        "document_type": "academic_certificate",
        "primary_subject": "Bachelor of Technology Degree Certificate",
        "currency": None,
        "summary": "Official B.Tech Degree Certificate issued to Rahul Sharma by Indian Institute of Technology Madras.",
        "extracted_fields": {
            "candidate_name": "Rahul Sharma",
            "roll_number": "CS22B045",
            "degree_title": "Bachelor of Technology in Computer Science",
            "institution": "Indian Institute of Technology Madras",
            "cgpa": "9.42 / 10.00",
            "division": "First Class with Distinction",
            "issue_date": "2026-07-15"
        },
        "tables": [
            {
                "title": "Core Semester Grades",
                "rows": [
                    {"Course": "Advanced Algorithms", "Grade": "S", "Credits": 4},
                    {"Course": "Computer Vision", "Grade": "A", "Credits": 4}
                ]
            }
        ],
        "full_text": "INDIAN INSTITUTE OF TECHNOLOGY MADRAS | Degree of Bachelor of Technology awarded to Rahul Sharma | Roll No: CS22B045 | CGPA: 9.42",
        "confidence": "high",
        "low_confidence_notes": []
    }

    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_c)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_e)):
        
        with open(cert_path, "rb") as f:
            res_upload = client.post("/api/documents/upload", files={"files": ("academic_transcript.png", f, "image/png")})
        assert res_upload.status_code == 200
        doc = res_upload.json()[0]
        doc_id = doc["id"]

    # Step 1: GET document for review
    res_get = client.get(f"/api/documents/{doc_id}")
    assert res_get.status_code == 200
    doc_data = res_get.json()
    assert doc_data["extracted_fields"]["candidate_name"] == "Rahul Sharma"
    assert doc_data["extracted_fields"]["roll_number"] == "CS22B045"
    assert doc_data["extracted_fields"]["cgpa"] == "9.42 / 10.00"
    assert len(doc_data["tables"]) == 1

    # Step 2: PATCH document review confirmation
    res_patch = client.patch(
        f"/api/documents/{doc_id}",
        json={
            "is_reviewed": True,
            "summary": "Verified Official B.Tech Certificate for Rahul Sharma.",
            "extracted_fields": {
                **doc_data["extracted_fields"],
                "verification_status": "Verified & Confirmed"
            }
        }
    )
    assert res_patch.status_code == 200
    updated_doc = res_patch.json()
    assert updated_doc["is_reviewed"] is True
    assert updated_doc["extracted_fields"]["verification_status"] == "Verified & Confirmed"

@pytest.mark.asyncio
async def test_all_five_image_formats_support():
    """
    Tests full pipeline (upload, in-memory processing, extraction, query) across
    PNG, JPG, JPEG, WEBP, and TIFF.
    """
    formats = [
        ("test_image.png", "PNG", "image/png"),
        ("test_image.jpg", "JPEG", "image/jpeg"),
        ("test_image.jpeg", "JPEG", "image/jpeg"),
        ("test_image.webp", "WEBP", "image/webp"),
        ("test_image.tiff", "TIFF", "image/tiff"),
        ("test_image.tif", "TIFF", "image/tiff"),
    ]

    for fname, pil_format, mime in formats:
        # Create in-memory test image
        buf = io.BytesIO()
        img = Image.new("RGB", (250, 250), color="#3B82F6")
        img.save(buf, format=pil_format)
        img_bytes = buf.getvalue()

        # Check ImageProcessor handles it cleanly
        tmp_path = Path(f"backend/uploads/{fname}")
        meta = ImageProcessor.process_and_save(img_bytes, tmp_path)
        assert Path(meta["saved_path"]).exists()

        clean_bytes, clean_mime = ImageProcessor.get_clean_image_bytes(str(tmp_path))
        assert len(clean_bytes) > 0
        assert clean_mime in ("image/png", "image/jpeg", "image/webp")

        mock_c = {
            "document_type": f"test_{pil_format.lower()}",
            "primary_subject": f"Test {pil_format} File",
            "key_fields": ["format", "size"],
            "is_text_heavy": False,
            "is_data_heavy": False,
            "is_non_informational": False
        }
        mock_e = {
            "document_type": f"test_{pil_format.lower()}",
            "primary_subject": f"Test {pil_format} File",
            "summary": f"Image successfully processed with format {pil_format}.",
            "extracted_fields": {"format": pil_format, "dimensions": "250x250"},
            "tables": [],
            "full_text": f"Format test for {fname}",
            "confidence": "high",
            "low_confidence_notes": []
        }

        with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_c)), \
             patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_e)):
            
            res_upload = client.post(
                "/api/documents/upload",
                files={"files": (fname, img_bytes, mime)}
            )
            assert res_upload.status_code == 200, f"Failed for format {fname}: {res_upload.text}"
            uploaded = res_upload.json()[0]
            assert uploaded["document_type"] == f"test_{pil_format.lower()}"
