import logging
import os
import re
from collections import Counter

from elevenlabs.client import ElevenLabs
from pydantic import BaseModel

from components.gemini_client import GeminiClient
from components.models.kb_entry import KBEntry

logger = logging.getLogger("hermits.voice.monthly_digest")

_VOICE_NAME_RE = re.compile(r'^[A-Za-z0-9_\- ]+$')


def _resolve_voice_id(client: ElevenLabs, voice_id_or_name: str) -> str:
    """Return voice_id unchanged if it looks like an ID; otherwise resolve by name."""
    # ElevenLabs voice IDs are ~20 char alphanumeric with no spaces
    if re.match(r'^[A-Za-z0-9]{15,}$', voice_id_or_name):
        return voice_id_or_name
    try:
        resp = client.voices.get_all()
        for v in resp.voices:
            if v.name.lower() == voice_id_or_name.lower():
                return v.voice_id
    except Exception as e:
        logger.warning("Could not resolve voice name '%s': %s", voice_id_or_name, e)
    # Known fallback: Rachel
    return "21m00Tcm4TlvDq8ikWAM"


class MonthlyDigestResult(BaseModel):
    transcript: str
    audio_bytes: bytes
    top_incidents: list[str]
    avg_resolution_minutes: float
    total_tickets: int
    most_common_root_cause: str

    model_config = {"arbitrary_types_allowed": True}


class MonthlyDigest:
    """Generates a monthly voice summary from KB entries."""

    def __init__(self, gemini_client: GeminiClient | None = None):
        self.gemini = gemini_client or GeminiClient()
        api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs = ElevenLabs(api_key=api_key)
        raw_voice = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")
        self.voice_id = _resolve_voice_id(self.elevenlabs, raw_voice)
        self.model_id = "eleven_multilingual_v2"
        logger.info("MonthlyDigest using voice_id=%s", self.voice_id)

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
        if not entries:
            return f"Month: {month}\nNo resolved incidents recorded this month."
        summaries = "\n".join(
            f"- {e.erp_log_snippet[:100]}, resolved in {e.resolution_time_minutes} min"
            for e in entries
        )
        return (
            f"Month: {month}\n"
            f"Total incidents: {len(entries)}\n\n"
            f"Incident summaries:\n{summaries}"
        )

    def _generate_transcript(self, entries: list[KBEntry], month: str) -> tuple[str, dict]:
        """Generate Gemini transcript + stats. No audio."""
        stats = self._build_stats(entries)
        system_prompt = (
            "You are producing a monthly IT operations voice report. "
            "Given the resolved incidents for the month, produce a professional spoken summary covering: "
            "total tickets resolved, average resolution time, top 3 root cause categories, "
            "most complex incident, and recommended preventive actions. "
            "Return plain text suitable for text-to-speech: no markdown, no bullet points, "
            "write it as flowing paragraphs. Keep it under 400 words."
        )
        user_message = self._build_prompt_text(entries, month)
        transcript = self.gemini.generate_text(system_prompt, user_message)
        return transcript, stats

    def generate_meta(self, entries: list[KBEntry], month: str) -> dict:
        """Transcript + statistics only — no ElevenLabs call."""
        transcript, stats = self._generate_transcript(entries, month)
        return {
            "transcript": transcript,
            "top_incidents": stats["top_incidents"],
            "avg_resolution_minutes": stats["avg_time"],
            "total_tickets": stats["total"],
            "most_common_root_cause": stats["most_common"],
        }

    def generate(self, entries: list[KBEntry], month: str) -> MonthlyDigestResult:
        """Full generation: transcript + ElevenLabs audio."""
        transcript, stats = self._generate_transcript(entries, month)
        logger.info("Generating ElevenLabs audio for month=%s (%d chars)", month, len(transcript))

        audio_gen = self.elevenlabs.text_to_speech.convert(
            voice_id=self.voice_id,
            text=transcript,
            model_id=self.model_id,
        )
        if hasattr(audio_gen, "__iter__") and not isinstance(audio_gen, bytes):
            audio_bytes = b"".join(audio_gen)
        else:
            audio_bytes = audio_gen

        return MonthlyDigestResult(
            transcript=transcript,
            audio_bytes=audio_bytes,
            top_incidents=stats["top_incidents"],
            avg_resolution_minutes=stats["avg_time"],
            total_tickets=stats["total"],
            most_common_root_cause=stats["most_common"],
        )
