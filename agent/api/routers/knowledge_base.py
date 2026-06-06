"""
Knowledge-base endpoints.

GET  /api/agent/ai/kb/entries             — list all KB entries
GET  /api/agent/ai/kb/entries/{entry_id}  — single entry by ID
POST /api/agent/ai/kb/match               — similarity search for a ticket
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import get_kb_store, get_kb_matcher
from api.utils import fetch_ticket_from_erp

router = APIRouter()


class KBMatchRequest(BaseModel):
    ticket_id: int
    recon_output: dict = {}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/entries", summary="List all knowledge-base entries")
def list_kb_entries():
    try:
        entries = get_kb_store().load_all()
        return {"count": len(entries), "entries": [e.model_dump() for e in entries]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries/{entry_id}", summary="Get a single KB entry by ID")
def get_kb_entry(entry_id: str):
    try:
        entry = get_kb_store().get_by_id(entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"KB entry '{entry_id}' not found")
        return entry.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match", summary="Find KB matches for a ticket")
async def match_kb(req: KBMatchRequest):
    """
    Runs token-overlap similarity against the knowledge base.
    Optionally pass recon_output to improve match quality.
    """
    try:
        ticket = await fetch_ticket_from_erp(req.ticket_id)
        matches = get_kb_matcher().match(ticket, req.recon_output)
        return {"count": len(matches), "matches": [m.model_dump() for m in matches]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
