"""
Lazy singletons shared across all agent API routers.
Each object is created on first access so the server can start without
every external API key (Gemini, ElevenLabs) being present.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.services.runner import HermitsAgent
    from components.knowledge_base.store import KBStore
    from components.knowledge_base.matcher import KBMatcher
    from components.triage.poller import TriagePoller
    from components.voice.ticket_summary import TicketVoiceSummary
    from components.voice.monthly_digest import MonthlyDigest

_agent: "HermitsAgent | None" = None
_kb_store: "KBStore | None" = None
_kb_matcher: "KBMatcher | None" = None
_voice_summary: "TicketVoiceSummary | None" = None
_monthly_digest: "MonthlyDigest | None" = None
_triage_poller: "TriagePoller | None" = None


def get_agent() -> "HermitsAgent":
    global _agent
    if _agent is None:
        from components.services.runner import HermitsAgent
        _agent = HermitsAgent()
    return _agent


def get_kb_store() -> "KBStore":
    global _kb_store
    if _kb_store is None:
        from components.knowledge_base.store import KBStore
        _kb_store = KBStore()
    return _kb_store


def get_kb_matcher() -> "KBMatcher":
    global _kb_matcher
    if _kb_matcher is None:
        from components.knowledge_base.matcher import KBMatcher
        _kb_matcher = KBMatcher()
    return _kb_matcher


def get_voice_summary() -> "TicketVoiceSummary":
    global _voice_summary
    if _voice_summary is None:
        from components.voice.ticket_summary import TicketVoiceSummary
        _voice_summary = TicketVoiceSummary()
    return _voice_summary


def get_monthly_digest() -> "MonthlyDigest":
    global _monthly_digest
    if _monthly_digest is None:
        from components.voice.monthly_digest import MonthlyDigest
        _monthly_digest = MonthlyDigest()
    return _monthly_digest


def get_triage_poller() -> "TriagePoller | None":
    return _triage_poller


def set_triage_poller(poller: "TriagePoller") -> None:
    global _triage_poller
    _triage_poller = poller
