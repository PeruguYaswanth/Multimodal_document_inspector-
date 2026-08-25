import os
import json
import re
import base64
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from google import genai
from google.genai import types
from PIL import Image
from app.config import settings
from app.services.image_processor import ImageProcessor

logger = logging.getLogger("vision_client")

class AIServiceUnavailableError(Exception):
    """Raised when Gemini API is temporarily unavailable (503 / 429) after all retries."""
    pass

def is_transient_error(e: Exception) -> bool:
    """
    Determines if an error is transient/temporary (503 UNAVAILABLE, 429 RESOURCE_EXHAUSTED,
    network drop) suitable for exponential backoff retries.
    Permanent errors (400, 401, 403, 404) are NOT retried.
    """
    from google.genai import errors
    if isinstance(e, errors.ServerError):
        return True
    if isinstance(e, errors.ClientError):
        if getattr(e, "code", None) == 429:
            return True
        err_msg = str(e).lower()
        if "resource_exhausted" in err_msg or "too many requests" in err_msg:
            return True
        return False
    if isinstance(e, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
        return True

    err_str = str(e).lower()
    transient_indicators = [
        "503", "unavailable", "high demand", "spikes in demand",
        "try again later", "overloaded", "resource_exhausted",
        "rate limit", "429", "timeout", "connection reset", "502", "504"
    ]
    return any(indicator in err_str for indicator in transient_indicators)

class VisionClient:
    def __init__(self):
        self.model = settings.GEMINI_MODEL

    def get_client(self) -> Optional[genai.Client]:
        """Dynamically retrieves an initialized Google Gen AI client from settings/env."""
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        if api_key and api_key.strip():
            return genai.Client(api_key=api_key.strip())
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

    async def call_gemini_api(
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
        Consolidated wrapper function for all Google Gemini API calls.
        Supports multimodal inputs, system instructions, structured generation config,
        exponential backoff retry for 503 UNAVAILABLE / 429 errors, and fallback model support.
        """
        client = self.get_client()
        if not client:
            raise RuntimeError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY or GOOGLE_API_KEY in "
                "the environment or backend/.env file to perform live multimodal image analysis."
            )

        gemini_contents: List[Any] = []

        # 1. Direct contents parameter
        if contents is not None:
            if isinstance(contents, list):
                gemini_contents.extend(contents)
            else:
                gemini_contents.append(contents)

        # 2. Direct image bytes or path
        elif image_bytes is not None:
            part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/jpeg")
            gemini_contents.append(part)
            if prompt:
                gemini_contents.append(prompt if isinstance(prompt, str) else str(prompt))
        elif image_path is not None:
            b_data, guessed_mime = ImageProcessor.get_clean_image_bytes(image_path)
            part = types.Part.from_bytes(data=b_data, mime_type=guessed_mime)
            gemini_contents.append(part)
            if prompt:
                gemini_contents.append(prompt if isinstance(prompt, str) else str(prompt))

        # 3. Parse prompt or messages structure
        else:
            raw_input = prompt if prompt is not None else messages
            if raw_input is None:
                raise ValueError("Either 'contents', 'prompt', 'messages', or 'image_path' must be provided.")

            if isinstance(raw_input, str):
                gemini_contents.append(raw_input)
            elif isinstance(raw_input, list):
                for item in raw_input:
                    if isinstance(item, str):
                        gemini_contents.append(item)
                    elif isinstance(item, dict):
                        if item.get("role") == "user" and isinstance(item.get("content"), list):
                            for sub in item["content"]:
                                if isinstance(sub, dict) and sub.get("type") == "image":
                                    src = sub.get("source", {})
                                    b64_str = src.get("data", "")
                                    m_type = src.get("media_type", "image/jpeg")
                                    b_data = base64.b64decode(b64_str)
                                    gemini_contents.append(types.Part.from_bytes(data=b_data, mime_type=m_type))
                                elif isinstance(sub, dict) and sub.get("type") == "text":
                                    gemini_contents.append(sub.get("text", ""))
                                elif isinstance(sub, str):
                                    gemini_contents.append(sub)
                        elif item.get("type") == "image":
                            src = item.get("source", {})
                            b64_str = src.get("data", "")
                            m_type = src.get("media_type", "image/jpeg")
                            b_data = base64.b64decode(b64_str)
                            gemini_contents.append(types.Part.from_bytes(data=b_data, mime_type=m_type))
                        elif item.get("type") == "text":
                            gemini_contents.append(item.get("text", ""))
                        else:
                            gemini_contents.append(json.dumps(item))
                    else:
                        gemini_contents.append(item)

        sys_val = system or system_prompt
        gen_config = types.GenerateContentConfig(
            system_instruction=sys_val,
            temperature=temperature,
            max_output_tokens=max_tokens
        )

        active_model = model or self.model
        retries_limit = max_retries if max_retries is not None else settings.GEMINI_MAX_RETRIES
        last_err = None

        for attempt in range(retries_limit + 1):
            try:
                def _do_call():
                    return client.models.generate_content(
                        model=active_model,
                        contents=gemini_contents,
                        config=gen_config
                    )

                response = await asyncio.to_thread(_do_call)
                return response.text
            except Exception as e:
                last_err = e
                # Check if error is transient
                if not is_transient_error(e):
                    logger.error(f"Permanent Gemini API failure (model={active_model}): {e}")
                    raise e

                logger.warning(
                    f"Gemini API transient failure on attempt {attempt + 1}/{retries_limit + 1}: {e} "
                    f"(model={active_model})"
                )

                # Attempt model fallback if primary model is experiencing 503 / high demand
                if active_model != settings.GEMINI_FALLBACK_MODEL and attempt >= 1:
                    logger.info(
                        f"Switching from '{active_model}' to fallback model '{settings.GEMINI_FALLBACK_MODEL}'"
                    )
                    active_model = settings.GEMINI_FALLBACK_MODEL

                if attempt < retries_limit:
                    # Exponential backoff: ~2s on attempt 0, ~4s on attempt 1, ~8s on attempt 2
                    delay = settings.GEMINI_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying Gemini call in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Gemini API remained unavailable after {retries_limit + 1} attempts: {last_err}",
                        exc_info=True
                    )
                    raise AIServiceUnavailableError(
                        "The AI service is temporarily unavailable. Please try again in a moment."
                    ) from last_err

    # Backward compatibility aliases
    async def call_claude_api(self, *args, **kwargs) -> str:
        return await self.call_gemini_api(*args, **kwargs)

    async def call_claude(self, *args, **kwargs) -> str:
        return await self.call_gemini_api(*args, **kwargs)

    async def _call_claude_with_retry(self, *args, **kwargs) -> str:
        return await self.call_gemini_api(*args, **kwargs)

    async def classify_image(self, image_path: str) -> Dict[str, Any]:
        """
        Stage 1A: Dynamic Image & Document Classification via Gemini 2.5 Flash Vision.
        """
        prompt = (
            "Analyze the attached image and identify what kind of image/document/subject it represents. "
            "It can be ANY category (e.g. food dish, receipt, invoice, handwritten note, ID card, medical record, "
            "parking ticket, whiteboard sketch, certificate, screenshot, artwork, physical object, landscape, etc.).\n\n"
            "Identify:\n"
            "1. 'document_type': Specific descriptive category of the image.\n"
            "2. 'primary_subject': The main subject, dish, or item depicted in plain terms (e.g. 'Curd Rice Dish with Pomegranate and Tadka', 'Metro Parking Ticket', 'Blood Chemistry Panel').\n"
            "3. 'key_fields': A list of 5-10 most important salient attributes a user would want extracted from this specific image.\n"
            "4. 'is_text_heavy': Boolean flag if the image is predominantly readable text.\n"
            "5. 'is_data_heavy': Boolean flag if the image contains rich tabular or structured data.\n"
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

        raw_text = await self.call_gemini_api(
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
        Stage 1B: Dynamic Attribute Extraction via Gemini 2.5 Flash Vision.
        """
        fields_str = ", ".join(key_fields) if key_fields else "salient visual and textual details"

        prompt = (
            f"Analyze this image ({document_type}: {primary_subject or 'General Image'}).\n"
            f"Extract all visible information corresponding to the requested attributes: {fields_str}.\n"
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
            '  "extracted_fields": { <dynamic key-value pairs representing all visible attributes, including both raw numbers and exact formatted strings> },\n'
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

        raw_text = await self.call_gemini_api(
            image_path=image_path,
            prompt=prompt,
            temperature=0.0
        )
        cleaned = self.clean_json_string(raw_text)
        return json.loads(cleaned)

    async def query_vision_direct(self, image_path: str, question: str) -> str:
        """
        Direct Image Vision Query: Re-inspects the raw image with Gemini Vision.
        """
        prompt = (
            f"You are inspecting the attached image directly to answer the following user question.\n"
            f"Question: {question}\n\n"
            f"Provide a clear, grounded, and concise answer directly based on what is visible in the image."
        )

        return await self.call_gemini_api(
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

        return await self.call_gemini_api(
            prompt=user_content,
            system=system_prompt,
            temperature=0.0
        )

vision_client = VisionClient()
