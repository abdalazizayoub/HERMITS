import json
import logging
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # Load environment variables from .env file

logger = logging.getLogger("hermits.gemini_client")


class GeminiParseError(Exception):
    pass


class GeminiClient:
    """Thin wrapper around google-generativeai with retry and JSON parsing."""

    def __init__(self):
        # genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def _strip_fences(self, text: str) -> str:
        text = text.strip()
        # Remove ```json ... ``` or ``` ... ``` fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int = 2,
    ) -> dict:
        """Call Gemini, strip markdown fences, parse JSON. Retry on parse failure."""
        full_prompt = f"{system_prompt}\n\n{user_message}"
        last_error = None

        for attempt in range(max_retries):
            try:
                # response = self.model.generate_content(full_prompt)
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt
                )
                raw = response.text
                cleaned = self._strip_fences(raw)
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning("JSON parse failed on attempt %d: %s", attempt + 1, e)

        raise GeminiParseError(
            f"Failed to parse Gemini JSON response after {max_retries} attempts: {last_error}"
        )

    def generate_text(self, system_prompt: str, user_message: str) -> str:
        """Call Gemini, return plain text response."""
        full_prompt = f"{system_prompt}\n\n{user_message}"
        # response = self.model.generate_content(full_prompt)
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        return response.text
