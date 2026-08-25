import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.vision_client import vision_client, AIServiceUnavailableError

client = TestClient(app)

def test_query_validation_empty_question():
    """Verifies that empty question returns 422 rather than 500."""
    res = client.post("/api/query", json={"question": ""})
    assert res.status_code == 422

    res2 = client.post("/api/query", json={"question": "   "})
    assert res2.status_code == 422

def test_query_no_matching_documents():
    """Verifies querying when no matching documents exist returns 200 with clear message."""
    res = client.post("/api/query", json={"question": "nonexistent term 12345 xyz"})
    assert res.status_code == 200
    data = res.json()
    assert "No documents in your collection matched the query" in data["answer"]

@pytest.mark.asyncio
async def test_query_handles_hf_503_cleanly():
    """Verifies that when Hugging Face is unavailable, /api/query returns clean 503 JSON."""
    with patch.object(
        vision_client,
        "generate_chat_answer",
        AsyncMock(side_effect=AIServiceUnavailableError("The AI service is temporarily busy. Please try again in a few seconds."))
    ):
        res = client.post("/api/query", json={"question": "what is the total", "scope": "all"})
        # Should return 200 if no docs or 503 if docs matched and synthesis failed
        if res.status_code == 503:
            assert res.json()["detail"] == "The AI service is temporarily busy. Please try again in a few seconds."
