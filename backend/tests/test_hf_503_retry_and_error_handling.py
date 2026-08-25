import pytest
import io
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from huggingface_hub.errors import HfHubHTTPError, OverloadedError
from PIL import Image

from app.main import app
from app.config import settings
from app.services.vision_client import (
    vision_client,
    AIServiceUnavailableError,
    AuthenticationError,
    ModelNotFoundError,
    is_transient_error
)

client = TestClient(app)

@pytest.mark.asyncio
async def test_transient_error_detection():
    """Verifies is_transient_error accurately differentiates transient vs permanent errors."""
    # OverloadedError / 503 -> Transient
    overloaded_err = OverloadedError("Model is overloaded")
    assert is_transient_error(overloaded_err) is True

    # 429 Rate Limit -> Transient
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    err_429 = HfHubHTTPError("Rate limit exceeded", response=mock_resp_429)
    assert is_transient_error(err_429) is True

    # 503 Service Unavailable -> Transient
    mock_resp_503 = MagicMock()
    mock_resp_503.status_code = 503
    err_503 = HfHubHTTPError("Service unavailable", response=mock_resp_503)
    assert is_transient_error(err_503) is True

    # 401 Unauthorized -> Permanent (Do not retry)
    mock_resp_401 = MagicMock()
    mock_resp_401.status_code = 401
    err_401 = HfHubHTTPError("Invalid token", response=mock_resp_401)
    assert is_transient_error(err_401) is False

    # 404 Model Not Found -> Permanent (Do not retry)
    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404
    err_404 = HfHubHTTPError("Model not found", response=mock_resp_404)
    assert is_transient_error(err_404) is False

@pytest.mark.asyncio
async def test_hf_retry_success_after_transient_failures():
    """Simulates 503 on attempts 0 & 1, then succeeds on attempt 2."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"status": "recovered_success"}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_resp_503 = MagicMock()
    mock_resp_503.status_code = 503
    server_503 = HfHubHTTPError("Service unavailable", response=mock_resp_503)
    mock_client.chat.completions.create.side_effect = [server_503, server_503, mock_response]

    with patch.object(vision_client, "get_client", return_value=mock_client), \
         patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        
        result = await vision_client.call_huggingface_api(
            prompt="Analyze document",
            max_retries=3
        )
        assert result == '{"status": "recovered_success"}'
        assert mock_client.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 2
        # Check exponential backoff delays passed to sleep
        mock_sleep.assert_any_call(settings.HF_RETRY_DELAY * 1) # 2.0s
        mock_sleep.assert_any_call(settings.HF_RETRY_DELAY * 2) # 4.0s

@pytest.mark.asyncio
async def test_permanent_error_fails_immediately():
    """Simulates 401 Unauthorized error and verifies immediate failure without retry."""
    mock_client = MagicMock()
    mock_resp_401 = MagicMock()
    mock_resp_401.status_code = 401
    auth_err = HfHubHTTPError("Invalid token", response=mock_resp_401)
    mock_client.chat.completions.create.side_effect = auth_err

    with patch.object(vision_client, "get_client", return_value=mock_client), \
         patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        
        with pytest.raises(AuthenticationError):
            await vision_client.call_huggingface_api(prompt="Test", max_retries=3)
            
        assert mock_client.chat.completions.create.call_count == 1
        assert mock_sleep.call_count == 0

@pytest.mark.asyncio
async def test_upload_endpoint_returns_clean_json_503_when_exhausted():
    """
    Verifies that when Hugging Face remains unavailable (503) through all retries,
    POST /api/documents/upload returns HTTP 503 JSON with exact detail message.
    """
    img_buf = io.BytesIO()
    Image.new("RGB", (200, 200), color="#10B981").save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    with patch.object(
        vision_client, 
        "classify_image", 
        AsyncMock(side_effect=AIServiceUnavailableError("The AI service is temporarily busy. Please try again in a few seconds."))
    ):
        res = client.post(
            "/api/documents/upload",
            files={"files": ("receipt.png", img_bytes, "image/png")}
        )
        assert res.status_code == 503
        data = res.json()
        assert data["detail"] == "The AI service is temporarily busy. Please try again in a few seconds."

def test_hf_token_env_fallback():
    """Verifies that setting HF_TOKEN allows client creation."""
    with patch.dict("os.environ", {"HF_TOKEN": "hf_test_token_12345"}):
        c = vision_client.get_client()
        assert c is not None
