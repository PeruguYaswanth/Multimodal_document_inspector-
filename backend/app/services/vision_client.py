import os
import json
import re
import base64
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from PIL import Image
from huggingface_hub import InferenceClient
from huggingface_hub.errors import (
    HfHubHTTPError,
    OverloadedError,
    InferenceTimeoutError,
    RepositoryNotFoundError,
    GatedRepoError,
    BadRequestError
)
from app.config import settings
from app.services.image_processor import ImageProcessor

logger = logging.getLogger("vision_client")

class AIServiceUnavailableError(Exception):
    """Raised when Hugging Face API is temporarily unavailable (503 / 502 / 429) after all retries."""
    pass

class AuthenticationError(Exception):
    """Raised when Hugging Face token is invalid or unauthorized."""
    pass

class ModelNotFoundError(Exception):
    """Raised when the requested Hugging Face model is not found or inaccessible."""
    pass

def is_transient_error(e: Exception) -> bool:
    """
    Determines if an error is transient/temporary (429 rate limit, 502/503/504 server overload,
    timeout, network drop) suitable for exponential backoff retries.
    Permanent errors (400, 401, 403, 404) are NOT retried.
    """
    if isinstance(e, (OverloadedError, InferenceTimeoutError)):
        return True

    if isinstance(e, HfHubHTTPError):
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code in (429, 500, 502, 503, 504):
            return True
        if status_code in (400, 401, 403, 404):
            return False

    if isinstance(e, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
        return True

    err_str = str(e).lower()
    transient_indicators = [
        "503", "502", "504", "429", "unavailable", "overloaded",
        "loading", "rate limit", "too many requests", "timeout",
        "timed out", "connection reset", "temporarily"
    ]
    return any(indicator in err_str for indicator in transient_indicators)

class VisionClient:
    def __init__(self):
        self.model = settings.HF_MODEL

    def get_client(self) -> Optional[InferenceClient]:
        """Dynamically retrieves an initialized Hugging Face InferenceClient from settings/env."""
        token = (
            settings.HF_TOKEN
            or os.getenv("HF_TOKEN", "")
            or os.getenv("HF_API_KEY", "")
            or os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
            or os.getenv("HUGGING_FACE_HUB_TOKEN", "")
        )
        if token and token.strip():
            return InferenceClient(token=token.strip())
        return None

    @staticmethod
    def clean_json_string(text: str) -> str:
        """Strips markdown code blocks, backticks, and extraneous whitespace."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            text = text[start_idx:end_idx + 1]
        return text

    async def call_huggingface_api(
        self,
        prompt: Optional[Union[str, List[Any]]] = None,
        messages: Optional[Union[List[Any], str]] = None,
        contents: Optional[Any] = None,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.0,
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Consolidated wrapper function for Hugging Face Multimodal Vision-Language API calls.
        Supports multimodal inputs (image data URLs + text prompts), system instructions,
        exponential backoff retry for 503/429/502 errors, and model fallback.
        """
        client = self.get_client()
        if not client:
            raise AuthenticationError(
                "Hugging Face token is not configured. Please set HF_TOKEN in "
                "the environment or backend/.env file to perform live multimodal image analysis."
            )

        hf_messages: List[Dict[str, Any]] = []

        # 1. System instruction
        sys_val = system or system_prompt
        if sys_val:
            hf_messages.append({"role": "system", "content": sys_val})

        # 2. Multimodal User Content
        user_content_parts: List[Dict[str, Any]] = []

        # Handle image input
        b_data = None
        media_type = mime_type or "image/jpeg"

        if image_bytes is not None:
            b_data = image_bytes
            media_type = mime_type or "image/jpeg"
        elif image_path is not None:
            b_data, media_type = ImageProcessor.get_clean_image_bytes(image_path)

        if b_data is not None:
            b64_str = base64.b64encode(b_data).decode("utf-8")
            data_url = f"data:{media_type};base64,{b64_str}"
            user_content_parts.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })

        # Handle prompt / messages text
        raw_text = ""
        if prompt is not None:
            raw_text = prompt if isinstance(prompt, str) else str(prompt)
        elif messages is not None:
            if isinstance(messages, str):
                raw_text = messages
            elif isinstance(messages, list):
                # Extract text and images from legacy message list structures
                for item in messages:
                    if isinstance(item, str):
                        raw_text += ("\n" + item) if raw_text else item
                    elif isinstance(item, dict):
                        if item.get("role") == "user" and isinstance(item.get("content"), list):
                            for sub in item["content"]:
                                if isinstance(sub, dict) and sub.get("type") == "image":
                                    src = sub.get("source", {})
                                    b64_s = src.get("data", "")
                                    m_t = src.get("media_type", "image/jpeg")
                                    user_content_parts.append({
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{m_t};base64,{b64_s}"}
                                    })
                                elif isinstance(sub, dict) and sub.get("type") == "text":
                                    raw_text += ("\n" + sub.get("text", "")) if raw_text else sub.get("text", "")
                        elif item.get("type") == "text":
                            raw_text += ("\n" + item.get("text", "")) if raw_text else item.get("text", "")
                        elif item.get("type") == "image":
                            src = item.get("source", {})
                            b64_s = src.get("data", "")
                            m_t = src.get("media_type", "image/jpeg")
                            user_content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{m_t};base64,{b64_s}"}
                            })
        elif contents is not None:
            raw_text = str(contents)

        if raw_text:
            user_content_parts.append({"type": "text", "text": raw_text})

        if user_content_parts:
            hf_messages.append({"role": "user", "content": user_content_parts})

        active_model = model or self.model
        retries_limit = max_retries if max_retries is not None else settings.HF_MAX_RETRIES
        last_err = None

        for attempt in range(retries_limit + 1):
            try:
                def _do_call():
                    return client.chat.completions.create(
                        model=active_model,
                        messages=hf_messages,
                        max_tokens=max_tokens,
                        temperature=temperature if temperature > 0 else None,
                    )

                response = await asyncio.to_thread(_do_call)
                return response.choices[0].message.content
            except Exception as e:
                last_err = e

                # Check for permanent authentication or model errors
                if isinstance(e, HfHubHTTPError):
                    status_code = getattr(getattr(e, "response", None), "status_code", None)
                    if status_code in (401, 403):
                        logger.error(f"Hugging Face authentication/permission error: {e}")
                        raise AuthenticationError(
                            "Invalid or unauthorized Hugging Face token. Ensure your token at https://huggingface.co/settings/tokens has 'Make calls to Inference Providers' permission enabled."
                        ) from e
                    elif status_code == 404:
                        logger.error(f"Hugging Face model '{active_model}' not found: {e}")
                        raise ModelNotFoundError(f"Hugging Face model '{active_model}' is unavailable.") from e

                if isinstance(e, (RepositoryNotFoundError, GatedRepoError)):
                    logger.error(f"Hugging Face model repository error: {e}")
                    raise ModelNotFoundError(f"Hugging Face model '{active_model}' is unavailable.") from e

                if not is_transient_error(e):
                    logger.error(f"Permanent Hugging Face API failure (model={active_model}): {e}")
                    raise e

                logger.warning(
                    f"Hugging Face API transient failure on attempt {attempt + 1}/{retries_limit + 1}: {e} "
                    f"(model={active_model})"
                )

                # Attempt model fallback on consecutive transient failure
                if active_model != settings.HF_FALLBACK_MODEL and attempt >= 1:
                    logger.info(
                        f"Switching from '{active_model}' to fallback model '{settings.HF_FALLBACK_MODEL}'"
                    )
                    active_model = settings.HF_FALLBACK_MODEL

                if attempt < retries_limit:
                    delay = settings.HF_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying Hugging Face call in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Hugging Face API remained unavailable after {retries_limit + 1} attempts: {last_err}",
                        exc_info=True
                    )
                    raise AIServiceUnavailableError(
                        "The AI service is temporarily busy. Please try again in a few seconds."
                    ) from last_err

    # Backward compatibility aliases
    async def call_gemini_api(self, *args, **kwargs) -> str:
        return await self.call_huggingface_api(*args, **kwargs)

    async def call_claude_api(self, *args, **kwargs) -> str:
        return await self.call_huggingface_api(*args, **kwargs)

    async def call_claude(self, *args, **kwargs) -> str:
        return await self.call_huggingface_api(*args, **kwargs)

    async def _call_claude_with_retry(self, *args, **kwargs) -> str:
        return await self.call_huggingface_api(*args, **kwargs)

    async def classify_image(self, image_path: str) -> Dict[str, Any]:
        """
        Stage 1A: Dynamic Image & Document Classification via Hugging Face Vision-Language Model.
        """
        logger.info(f"[VISION] Processing image with Qwen... (Stage 1A Classification: {image_path})")
        prompt = (
            "Analyze the attached image and identify what kind of image/document/subject it represents. "
            "It can be ANY category (e.g. food dish, receipt, invoice, handwritten note, ID card, medical record, "
            "parking ticket, whiteboard, form, diagram, landscape, screenshot, etc.). Do not restrict to office documents.\n\n"
            "Produce the following analysis:\n"
            "1. 'document_type': A concise descriptive category name in snake_case (e.g. 'food_dish', 'receipt', 'blood_test_report', 'parking_ticket', 'certificate').\n"
            "2. 'primary_subject': A specific, highly informative title for the subject (e.g. 'South Indian Curd Rice with Mustard Tempering', 'San Francisco Parking Violation', 'IIT Madras Degree Certificate').\n"
            "3. 'key_fields': A list of the 4 to 8 most important attribute field names that should be extracted from this specific subject.\n"
            "4. 'is_text_heavy': Boolean flag if the image contains substantial readable text.\n"
            "5. 'is_data_heavy': Boolean flag if the image contains quantitative data, prices, dates, marks, or tables.\n"
            "6. 'is_non_informational': Boolean flag ONLY if the image is an abstract pattern, blank canvas, or completely unidentifiable content.\n\n"
            "Return strict JSON with this exact schema:\n"
            "{\n"
            '  "document_type": string,\n'
            '  "primary_subject": string,\n'
            '  "key_fields": [string],\n'
            '  "is_text_heavy": boolean,\n'
            '  "is_data_heavy": boolean,\n'
            '  "is_non_informational": boolean\n'
            "}\n"
            "Never wrap in markdown fences. Return ONLY the raw JSON object."
        )

        raw_text = await self.call_huggingface_api(
            image_path=image_path,
            prompt=prompt,
            temperature=0.0
        )
        cleaned = self.clean_json_string(raw_text)
        return json.loads(cleaned)

    async def extract_dynamic_fields(
        self,
        image_path: str,
        document_type: str,
        primary_subject: Optional[str],
        key_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Stage 1B: Dynamic Attribute Extraction via Hugging Face Vision-Language Model.
        """
        logger.info(f"[VISION] Processing image with Qwen... (Stage 1B Extraction: '{primary_subject or document_type}')")
        fields_str = ", ".join(key_fields) if key_fields else "salient visual and textual details"

        prompt = (
            f"Analyze this image ({document_type}: {primary_subject or 'General Image'}).\n"
            f"Extract all visible information corresponding to the requested attributes: {fields_str}.\n"
            "Also capture salient visual features (e.g. colors of key objects/plates/containers, materials, layout, arrangement) into extracted_fields.\n"
            "Also transcribe any visible text as-is, and extract any tables or structured key-values.\n\n"
            "CURRENCY AND NUMBER FORMATTING RULES:\n"
            "1. Detect the currency symbol or code shown in the image (e.g. ₹, $, €, £, INR, USD). Do not assume USD by default. Use the exact symbol as it appears.\n"
            "2. Transcribe every monetary amount EXACTLY as it appears in the image into a formatted string (e.g. '₹1,25,450.00', '₹500', '$1,250.75'). "
            "Preserve original digit grouping (e.g. Indian lakh grouping vs Western grouping), decimal precision (e.g. ₹500 vs ₹500.00), and symbol position.\n"
            "3. For every monetary amount, store BOTH the raw numeric float (e.g. 125450.0) for computation AND the original exact formatted string (e.g. '₹1,25,450.00') for display.\n\n"
            "Return strict JSON with this exact structure:\n"
            "{\n"
            f'  "document_type": "{document_type}",\n'
            f'  "primary_subject": "{primary_subject or "Main Subject"}",\n'
            '  "currency": string (detected currency symbol/code like "₹", "$", "€", "£", or null if not applicable),\n'
            '  "summary": string (1-2 sentence detailed, factual summary of the image and its contents),\n'
            '  "extracted_fields": { <dynamic key-value pairs representing all visible attributes, colors, objects, numbers, and formatted strings> },\n'
            '  "tables": [ { "title": string, "rows": [ { <column_name>: <cell_value> } ] } ],\n'
            '  "full_text": string (all visible readable text transcribed accurately, or empty string if no text),\n'
            '  "confidence": "high" | "medium" | "low",\n'
            '  "low_confidence_notes": [string]\n'
            "}\n\n"
            "Rules:\n"
            "- Never hallucinate or make up details not present in the image.\n"
            "- If a field is not visible in the image, set its value to null.\n"
            "- Return ONLY valid raw JSON with no markdown formatting."
        )

        raw_text = await self.call_huggingface_api(
            image_path=image_path,
            prompt=prompt,
            temperature=0.0
        )
        cleaned = self.clean_json_string(raw_text)
        return json.loads(cleaned)

    async def query_vision_direct(self, image_path: str, question: str) -> str:
        """
        Direct Image Vision Query: Re-inspects the raw image with Hugging Face Vision.
        """
        prompt = (
            f"You are inspecting the attached image directly to answer the following user question.\n"
            f"Question: {question}\n\n"
            f"Provide a clear, grounded, and concise answer directly based on what is visible in the image."
        )

        return await self.call_huggingface_api(
            image_path=image_path,
            prompt=prompt,
            temperature=0.2
        )

    async def generate_chat_answer(
        self,
        question: str,
        context_data: List[Dict[str, Any]],
        math_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Stage 2 Synthesis: Answers the user's natural language question grounded in extracted records.
        """
        system_prompt = (
            "You are a multimodal document and image intelligence assistant.\n"
            "STRICT CONCISE ANSWER RULES:\n"
            "1. Answer the question directly and concisely, in one short sentence or phrase.\n"
            "2. Do not include source citations, document names, computation methods, or reference lists.\n"
            "3. Do not add unnecessary context beyond what was asked — answer only what the question asks, nothing more.\n"
            "   Example: for 'overall total how many marks got', the answer should be '565 marks' or 'The total is 565 marks.'\n"
            "4. When answering about a single document, return the stored exact formatted values verbatim.\n"
            "5. If currencies are mixed across multiple documents, report the separate subtotals concisely.\n"
            "6. Never output debug labels, computational method names, or preamble text."
        )

        user_content = f"User Question: {question}\n\n"
        if math_result:
            user_content += f"DETERMINISTIC CODE COMPUTATION:\n{json.dumps(math_result, indent=2)}\n\n"

        user_content += f"DOCUMENT CONTEXT RECORDS:\n{json.dumps(context_data, indent=2)}\n\n"
        user_content += "Provide ONLY the direct, concise answer to the question based on the records above."

        return await self.call_huggingface_api(
            prompt=user_content,
            system=system_prompt,
            temperature=0.0
        )

vision_client = VisionClient()
