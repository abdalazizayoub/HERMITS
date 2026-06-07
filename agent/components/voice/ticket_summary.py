import logging
import os
import re

from elevenlabs.client import ElevenLabs

from components.models.kb_entry import KBMatch
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.voice.ticket_summary")


def _resolve_voice_id(client: ElevenLabs, voice_id_or_name: str) -> str:
    if re.match(r'^[A-Za-z0-9]{15,}$', voice_id_or_name):
        return voice_id_or_name
    try:
        resp = client.voices.get_all()
        for v in resp.voices:
            if v.name.lower() == voice_id_or_name.lower():
                return v.voice_id
    except Exception as e:
        logger.warning("Could not resolve voice name '%s': %s", voice_id_or_name, e)
    return "21m00Tcm4TlvDq8ikWAM"  # Rachel fallback


class TicketVoiceSummary:
    """On-demand: technician clicks a button, gets an MP3 of the ticket summary."""

    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        self.client = ElevenLabs(api_key=api_key)
        raw_voice = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")
        self.voice_id = _resolve_voice_id(self.client, raw_voice)
        self.model_id = "eleven_multilingual_v2"
        logger.info("TicketVoiceSummary using voice_id=%s", self.voice_id)

    def _build_text(self, ticket: Ticket, kb_matches: list[KBMatch]) -> str:
        priority_phrase = {
            "critical": "This is a CRITICAL priority ticket.",
            "high": "This is a high priority ticket.",
            "medium": "This is a medium priority ticket.",
            "low": "This is a low priority ticket.",
        }.get(ticket.priority.lower(), "")

        text = (
            f"Ticket {ticket.id} for customer {ticket.customer_name}. "
            f"{priority_phrase} "
            f"Title: {ticket.title}. "
            f"{ticket.description[:500]}"
        )

        if kb_matches:
            best = kb_matches[0]
            text += (
                f" Similar past incident: {best.entry.root_cause} — "
                f"resolved in {best.entry.resolution_time_minutes} minutes."
            )

        return text

    def generate(self, ticket: Ticket, kb_matches: list[KBMatch]) -> bytes:
        text = self._build_text(ticket, kb_matches)
        logger.info("Generating voice summary for ticket %s", ticket.id)
        audio = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id=self.model_id,
        )
        if hasattr(audio, "__iter__") and not isinstance(audio, bytes):
            return b"".join(audio)
        return audio
