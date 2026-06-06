from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from components.models.kb_entry import KBEntry, KBMatch, ReconFingerprint, TicketFingerprint
from components.models.ticket import Ticket


def _make_ticket() -> Ticket:
    return Ticket(
        id="T010",
        title="nginx down",
        description="nginx not responding on port 80",
        customer_name="TestCo",
        priority="high",
        status="open",
        created_at=datetime(2026, 6, 1),
        service_hint="nginx",
    )


def _make_kb_match() -> KBMatch:
    entry = KBEntry(
        ticket_fingerprint=TicketFingerprint(
            service_hint="nginx",
            error_patterns=[],
            symptom_keywords=["nginx"],
        ),
        recon_fingerprint=ReconFingerprint(
            failed_services=["nginx"],
            top_errors=[],
            disk_critical=False,
        ),
        root_cause="nginx config syntax error",
        fix_commands=["nginx -t", "systemctl restart nginx"],
        validation_passed=True,
        resolution_time_minutes=20,
        technician_id="tech1",
        erp_log_snippet="Fixed nginx",
    )
    return KBMatch(entry=entry, similarity_score=0.85, confidence_boost=0.34)


class TestTicketVoiceSummary:
    def test_calls_elevenlabs_with_ticket_info(self):
        fake_audio = b"fake_audio_bytes"

        with patch("hermits.voice.ticket_summary.ElevenLabs") as MockElevenLabs:
            mock_tts = MagicMock()
            mock_tts.text_to_speech.convert.return_value = iter([fake_audio])
            MockElevenLabs.return_value = mock_tts

            from components.voice.ticket_summary import TicketVoiceSummary
            tts = TicketVoiceSummary()

            ticket = _make_ticket()
            kb_matches = [_make_kb_match()]

            result = tts.generate(ticket, kb_matches)

            assert result == fake_audio
            mock_tts.text_to_speech.convert.assert_called_once()
            call_kwargs = mock_tts.text_to_speech.convert.call_args
            text_arg = call_kwargs.kwargs.get("text") or call_kwargs.args[1] if call_kwargs.args else ""
            # Verify ticket info is in the spoken text
            assert "nginx" in text_arg.lower() or "T010" in text_arg

    def test_includes_kb_match_in_text(self):
        fake_audio = b"audio"

        with patch("hermits.voice.ticket_summary.ElevenLabs") as MockElevenLabs:
            mock_tts = MagicMock()
            mock_tts.text_to_speech.convert.return_value = iter([fake_audio])
            MockElevenLabs.return_value = mock_tts

            from components.voice.ticket_summary import TicketVoiceSummary
            tts = TicketVoiceSummary()
            tts._build_text(_make_ticket(), [_make_kb_match()])

            text = tts._build_text(_make_ticket(), [_make_kb_match()])
            assert "20 minutes" in text
            assert "nginx config syntax error" in text

    def test_no_kb_matches(self):
        fake_audio = b"audio"

        with patch("hermits.voice.ticket_summary.ElevenLabs") as MockElevenLabs:
            mock_tts = MagicMock()
            mock_tts.text_to_speech.convert.return_value = iter([fake_audio])
            MockElevenLabs.return_value = mock_tts

            from components.voice.ticket_summary import TicketVoiceSummary
            tts = TicketVoiceSummary()
            text = tts._build_text(_make_ticket(), [])
            assert "Similar" not in text


class TestMonthlyDigest:
    def _make_entry(self) -> KBEntry:
        return KBEntry(
            ticket_fingerprint=TicketFingerprint(
                service_hint="nginx",
                error_patterns=[],
                symptom_keywords=["nginx"],
            ),
            recon_fingerprint=ReconFingerprint(
                failed_services=[],
                top_errors=[],
                disk_critical=False,
            ),
            root_cause="nginx config error",
            fix_commands=["systemctl restart nginx"],
            validation_passed=True,
            resolution_time_minutes=30,
            technician_id="tech1",
            erp_log_snippet="Ticket T001: fixed nginx",
        )

    def test_calls_gemini_then_elevenlabs(self):
        fake_audio = b"digest_audio"
        fake_transcript = "This month we resolved 5 tickets."

        with (
            patch("hermits.voice.monthly_digest.ElevenLabs") as MockElevenLabs,
            patch("hermits.voice.monthly_digest.GeminiClient") as MockGemini,
        ):
            mock_tts = MagicMock()
            mock_tts.text_to_speech.convert.return_value = iter([fake_audio])
            MockElevenLabs.return_value = mock_tts

            mock_gemini = MagicMock()
            mock_gemini.generate_text.return_value = fake_transcript
            MockGemini.return_value = mock_gemini

            from components.voice.monthly_digest import MonthlyDigest
            digest = MonthlyDigest()
            entries = [self._make_entry() for _ in range(3)]
            result = digest.generate(entries, "2026-06")

            # Gemini was called first
            mock_gemini.generate_text.assert_called_once()
            # ElevenLabs was called with the transcript
            mock_tts.text_to_speech.convert.assert_called_once()
            tts_call = mock_tts.text_to_speech.convert.call_args
            text_used = tts_call.kwargs.get("text", "")
            assert text_used == fake_transcript

            assert result.transcript == fake_transcript
            assert result.audio_bytes == fake_audio
            assert result.total_tickets == 3
            assert result.avg_resolution_minutes == 30.0
