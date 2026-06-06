"""
Voice endpoints — on-demand MP3 summaries and monthly digest.

GET  /api/agent/ai/voice/summary/{ticket_id}  — ticket summary as MP3
POST /api/agent/ai/voice/digest               — monthly digest metadata
POST /api/agent/ai/voice/digest/audio         — monthly digest as MP3
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from api.dependencies import get_voice_summary, get_kb_matcher, get_monthly_digest, get_kb_store
from api.utils import fetch_ticket_from_erp

router = APIRouter()


class DigestRequest(BaseModel):
    month: str  # e.g. "2025-06"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/summary/{ticket_id}", summary="On-demand MP3 summary for a ticket")
async def ticket_voice_summary(ticket_id: int):
    """
    Generates an ElevenLabs MP3 briefing for the given ticket, including the
    best matching past incident from the knowledge base if one exists.
    Returns audio/mpeg bytes.
    """
    try:
        ticket = await fetch_ticket_from_erp(ticket_id)
        kb_matches = get_kb_matcher().match(ticket, {})
        audio_bytes = get_voice_summary().generate(ticket, kb_matches)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/digest", summary="Monthly digest metadata (no audio)")
def monthly_digest_meta(req: DigestRequest):
    """
    Generates a monthly IT-ops narrative from resolved KB entries.
    Returns transcript + statistics (no audio bytes to keep payload small).
    """
    try:
        entries = get_kb_store().load_all()
        result = get_monthly_digest().generate(entries, req.month)
        return {
            "month": req.month,
            "transcript": result.transcript,
            "top_incidents": result.top_incidents,
            "avg_resolution_minutes": result.avg_resolution_minutes,
            "total_tickets": result.total_tickets,
            "most_common_root_cause": result.most_common_root_cause,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/digest/audio", summary="Monthly digest as MP3")
def monthly_digest_audio(req: DigestRequest):
    """
    Same as /digest but returns the audio as audio/mpeg bytes.
    """
    try:
        entries = get_kb_store().load_all()
        result = get_monthly_digest().generate(entries, req.month)
        return Response(content=result.audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
