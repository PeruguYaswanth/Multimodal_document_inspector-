import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
from app.services.vision_client import vision_client

@pytest.mark.asyncio
async def test_call_huggingface_wrapper():
    """
    Verifies that call_huggingface_api correctly formats multimodal contents and
    passes ChatCompletionInput to client.chat.completions.create.
    """
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"status": "hf_success"}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    with patch.object(vision_client, "get_client", return_value=mock_client):
        # 1. Test text prompt with system instruction and temperature
        res1 = await vision_client.call_huggingface_api(
            prompt="Analyze this document",
            system="You are an expert analyst",
            temperature=0.2,
            max_tokens=2048
        )
        assert res1 == '{"status": "hf_success"}'
        call_kwargs1 = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs1["model"] == vision_client.model
        assert call_kwargs1["temperature"] == 0.2
        assert call_kwargs1["max_tokens"] == 2048
        messages = call_kwargs1["messages"]
        assert any(m.get("role") == "system" and m.get("content") == "You are an expert analyst" for m in messages)
        assert any(m.get("role") == "user" for m in messages)

        # 2. Test multimodal image bytes input
        img_bytes = b"fake_image_bytes"
        res2 = await vision_client.call_huggingface_api(
            prompt="Extract table",
            image_bytes=img_bytes,
            mime_type="image/png",
            temperature=0.0
        )
        assert res2 == '{"status": "hf_success"}'
        call_kwargs2 = mock_client.chat.completions.create.call_args.kwargs
        messages2 = call_kwargs2["messages"]
        user_msg = next(m for m in messages2 if m.get("role") == "user")
        assert any(p.get("type") == "image_url" for p in user_msg["content"])
        assert any(p.get("type") == "text" for p in user_msg["content"])

        # 3. Test backward compatibility alias
        res3 = await vision_client.call_gemini_api(
            prompt="Legacy call",
            system_prompt="Legacy prompt",
            temperature=0.3
        )
        assert res3 == '{"status": "hf_success"}'
