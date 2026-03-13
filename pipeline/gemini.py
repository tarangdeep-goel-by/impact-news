"""Gemini AI client for Impact News pipeline."""

import json
import logging
import re

from google import genai

from config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper around Google GenAI SDK for tag extraction and explanation."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def call(self, prompt: str, model: str | None = None) -> str:
        """Send a prompt to Gemini and return raw text response."""
        model = model or settings.gemini_model
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(temperature=0.3),
        )
        return response.text


def parse_json_response(text: str) -> list | dict:
    """Strip markdown fences, find JSON boundaries, parse.

    Handles both JSON arrays and objects. Reuses pattern from
    n8n-news-agent/src/analyzer.py parse_ai_response().
    """
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"```\s*$", "", cleaned)

    # Try array first, then object
    first_bracket = cleaned.find("[")
    first_brace = cleaned.find("{")

    if first_bracket == -1 and first_brace == -1:
        raise ValueError(f"No JSON found in response: {text[:200]}")

    # Pick whichever comes first
    if first_brace == -1 or (first_bracket != -1 and first_bracket < first_brace):
        # Array
        last = cleaned.rfind("]")
        if last == -1:
            raise ValueError("Unclosed JSON array in response")
        json_str = cleaned[first_bracket : last + 1]
    else:
        # Object
        last = cleaned.rfind("}")
        if last == -1:
            raise ValueError("Unclosed JSON object in response")
        json_str = cleaned[first_brace : last + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from Gemini response: %s", text[:500])
        raise
