import json
import logging
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("hermits.gemini_client")

_JSON_DECODER = json.JSONDecoder()

# Matches backslash followed by any character that is NOT a valid JSON escape.
# Valid JSON escapes: \" \\ \/ \b \f \n \r \t \uXXXX
_INVALID_ESCAPE_RE = re.compile(r'\\([^"\\/bfnrtu])')


def _fix_json_escapes(text: str) -> str:
    """Drop backslashes that precede non-JSON-escape characters (e.g. \\% \\{ \\})."""
    return _INVALID_ESCAPE_RE.sub(r'\1', text)


class GeminiParseError(Exception):
    pass


def _extract_first_json_object(text: str) -> dict:
    """
    Scan text char-by-char for the first '{' and attempt to decode a full
    JSON object from that position. Handles thinking-model preamble and
    trailing text gracefully.
    """
    for i, ch in enumerate(text):
        if ch == '{':
            try:
                obj, _ = _JSON_DECODER.raw_decode(text, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("No valid JSON object found", text, 0)


class GeminiClient:
    """Thin wrapper around google-generativeai with retry and JSON parsing."""

    _JSON_MODEL = "gemini-3.5-flash"
    _TEXT_MODEL = "gemini-3.5-flash"

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def _strip_fences(self, text: str) -> str:
        text = text.strip()
        # Strip thinking-model XML tags that some models prepend
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int = 3,
    ) -> dict:
        """
        Call Gemini with JSON output mode enforced, parse and return a dict.
        Uses gemini-2.0-flash (no thinking tokens) for fast, reliable JSON output.
        Falls back to scanning the raw response for the first valid JSON object.
        Retries on parse failure.
        """
        last_error: Exception | None = None
        raw = ""

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self._JSON_MODEL,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0.0,
                    ),
                )
                raw = response.text or ""

                # Primary: direct parse after stripping fences + fixing escapes
                cleaned = _fix_json_escapes(self._strip_fences(raw))
                try:
                    result = json.loads(cleaned)
                    logger.debug("generate_json parsed keys=%s", list(result.keys()) if isinstance(result, dict) else type(result).__name__)
                    return result
                except json.JSONDecodeError:
                    pass

                # Fallback: scan for first valid JSON object in cleaned text
                result = _extract_first_json_object(cleaned)
                logger.debug("generate_json fallback-parsed keys=%s", list(result.keys()))
                return result

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    "JSON parse failed on attempt %d: %s | raw=%r",
                    attempt + 1, e, raw[:500],
                )
            except Exception as e:
                last_error = e
                logger.warning("Gemini call failed on attempt %d: %s | raw=%r", attempt + 1, e, raw[:300])

        raise GeminiParseError(
            f"Gemini failed after {max_retries} attempts: {last_error}"
        )

    def generate_text(self, system_prompt: str, user_message: str) -> str:
        """Call Gemini with a system instruction and return plain text."""
        response = self.client.models.generate_content(
            model=self._TEXT_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        return response.text or ""
