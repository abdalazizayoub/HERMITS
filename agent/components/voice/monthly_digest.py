import logging
import os
from collections import Counter

from elevenlabs.client import ElevenLabs
from pydantic import BaseModel

from components.gemini_client import GeminiClient
from components.models.kb_entry import KBEntry

logger = logging.getLogger("hermits.voice.monthly_digest")


class MonthlyDigestResult(BaseModel):
    transcript: str
    audio_bytes: bytes
    top_incidents: list[str]
    avg_resolution_minutes: float
    total_tickets: int
    most_common_root_cause: str


class MonthlyDigest:
    """Generates a monthly voice summary from KB entries."""

    def __init__(self, gemini_client: GeminiClient | None = None):
        self.gemini = gemini_client or GeminiClient()
        api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs = ElevenLabs(api_key=api_key)
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")
        self.model_id = "eleven_multilingual_v2"

    def _build_stats(self, entries: list[KBEntry]) -> dict:
        total = len(entries)
        avg_time = (
            sum(e.resolution_time_minutes for e in entries) / total if total else 0.0
        )
        root_causes = [e.root_cause[:60] for e in entries]
        most_common = Counter(root_causes).most_common(1)[0][0] if root_causes else "N/A"
        top_incidents = [e.erp_log_snippet[:120] for e in entries[:3]]
        return {
            "total": total,
            "avg_time": avg_time,
            "most_common": most_common,
            "top_incidents": top_incidents,
        }

    def _build_prompt_text(self, entries: list[KBEntry], month: str) -> str:
        summaries = "\n".join(
            f"- Ticket {e.erp_log_snippet[:100]}, resolved in {e.resolution_time_minutes} min"
            for e in entries
        )
        return (
            f"Month: {month}\n"
            f"Total incidents: {len(entries)}\n\n"
            f"Incident summaries:\n{summaries}"
        )

    def generate(self, entries: list[KBEntry], month: str) -> MonthlyDigestResult:
        stats = self._build_stats(entries)

        system_prompt = (
            "You are producing a monthly IT operations voice report. "
            "Given the resolved incidents for the month, produce a professional spoken summary covering: "
            "total tickets resolved, average resolution time, top 3 root cause categories, "
            "most complex incident, and recommended preventive actions. "
            "Return plain text suitable for text-to-speech: no markdown, no bullet points, "
            "write it as flowing paragraphs."
        )
        user_message = self._build_prompt_text(entries, month)

        transcript = self.gemini.generate_text(system_prompt, user_message)
        logger.info("Monthly digest transcript generated for %s (%d chars)", month, len(transcript))

        audio_gen = self.elevenlabs.text_to_speech.convert(
            voice_id=self.voice_id,
            text=transcript,
            model_id=self.model_id,
        )
        audio_bytes = b"".join(audio_gen) if hasattr(audio_gen, "__iter__") and not isinstance(audio_gen, bytes) else audio_gen

        return MonthlyDigestResult(
            transcript=transcript,
            audio_bytes=audio_bytes,
            top_incidents=stats["top_incidents"],
            avg_resolution_minutes=stats["avg_time"],
            total_tickets=stats["total"],
            most_common_root_cause=stats["most_common"],
        )
