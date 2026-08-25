import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
from app.services.vision_client import vision_client

@pytest.mark.asyncio
async def test_call_gemini_wrapper():
    """
    Verifies that call_gemini_api correctly formats multimodal contents and
    passes GenerateContentConfig to client.models.generate_content.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"status": "gemini_success"}'
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(vision_client, "get_client", return_value=mock_client):
        # 1. Test text prompt with system instruction and temperature
        res1 = await vision_client.call_gemini_api(
            prompt="Analyze this document",
            system="You are an expert analyst",
            temperature=0.2,
            max_tokens=2048
        )
        assert res1 == '{"status": "gemini_success"}'
        call_kwargs1 = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs1["model"] == vision_client.model
        assert "Analyze this document" in call_kwargs1["contents"]
        assert call_kwargs1["config"].system_instruction == "You are an expert analyst"
        assert call_kwargs1["config"].temperature == 0.2
        assert call_kwargs1["config"].max_output_tokens == 2048

        # 2. Test multimodal image bytes input
        img_bytes = b"fake_image_bytes"
        res2 = await vision_client.call_gemini_api(
            prompt="Extract table",
            image_bytes=img_bytes,
            mime_type="image/png",
            temperature=0.0
        )
        assert res2 == '{"status": "gemini_success"}'
        call_kwargs2 = mock_client.models.generate_content.call_args.kwargs
        assert len(call_kwargs2["contents"]) == 2
        assert call_kwargs2["config"].temperature == 0.0

        # 3. Test backward compatibility alias
        res3 = await vision_client.call_claude_api(
            prompt="Legacy call",
            system_prompt="Legacy prompt",
            temperature=0.3
        )
        assert res3 == '{"status": "gemini_success"}'
        call_kwargs3 = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs3["config"].system_instruction == "Legacy prompt"
        assert call_kwargs3["config"].temperature == 0.3
