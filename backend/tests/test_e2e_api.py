import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.vision_client import vision_client

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model" in data

def test_load_and_generalize_sample_dataset():
    mock_classify = {
        "document_type": "generic_document",
        "primary_subject": "Test Document",
        "key_fields": ["title", "content"],
        "is_text_heavy": True,
        "is_data_heavy": False,
        "is_non_informational": False
    }
    mock_extract = {
        "document_type": "generic_document",
        "primary_subject": "Test Document",
        "summary": "Sample test document summary.",
        "extracted_fields": {"title": "Test Item", "amount": 25.0},
        "tables": [],
        "full_text": "Sample test document content.",
        "confidence": "high",
        "low_confidence_notes": []
    }

    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_classify)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_extract)):
        response = client.post("/api/sample-data/load-all")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["documents"]) >= 4

def test_list_and_filter_documents():
    response = client.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1

def test_update_and_confirm_review():
    docs_res = client.get("/api/documents")
    docs = docs_res.json()
    assert len(docs) > 0
    first_doc = docs[0]

    updated_fields = dict(first_doc.get("extracted_fields") or {})
    updated_fields["manual_verification_tag"] = "TEST_CONFIRMED"

    update_res = client.patch(
        f"/api/documents/{first_doc['id']}",
        json={
            "primary_subject": "Updated Subject Title",
            "extracted_fields": updated_fields,
            "is_reviewed": True,
            "confidence": "high"
        }
    )
    assert update_res.status_code == 200
    updated_doc = update_res.json()
    assert updated_doc["primary_subject"] == "Updated Subject Title"
    assert updated_doc["extracted_fields"]["manual_verification_tag"] == "TEST_CONFIRMED"
    assert updated_doc["is_reviewed"] is True

def test_query_cross_document():
    query_payload = {
        "question": "Summarize the primary subjects in my documents.",
        "scope": "all"
    }
    with patch.object(vision_client, "generate_chat_answer", AsyncMock(return_value="The documents include sample testing documents.")):
        res = client.post("/api/query", json=query_payload)
        assert res.status_code == 200
        data = res.json()
        assert len(data["sources"]) > 0
        assert "sample testing documents" in data["answer"]
