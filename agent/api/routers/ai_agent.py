"""
AI agent endpoints — the two-phase troubleshooting workflow.

POST /api/agent/ai/phase1   — open ticket → pillar spec + KB pre-match
POST /api/agent/ai/phase2   — post-recon  → ranked hypotheses + safety checks
POST /api/agent/ai/complete — close ticket → pillar validation + ERP draft + KB write
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from components.models.pillar import PillarResult
from api.dependencies import get_agent
from api.utils import fetch_ticket_from_erp

router = APIRouter()

# In-memory store: ticket_id → Phase1Result
# Bridges the gap between the two HTTP calls (phase1 → phase2).
_phase1_store: dict[int, object] = {}


# ── Request models ─────────────────────────────────────────────────────────────

class Phase1Request(BaseModel):
    ticket_id: int
    technician_id: str = "default"


class Phase2Request(BaseModel):
    ticket_id: int
    technician_id: str = "default"
    recon_output: dict
    pillar_baseline: PillarResult


class CompleteRequest(BaseModel):
    ticket_id: int
    chosen_hypothesis_index: int
    pillar_after_results: PillarResult
    executed_steps: list[dict]
    technician_id: str
    technician_notes: str = ""
    resolution_time_minutes: int
    command_decisions: list[tuple[str, bool]] = []


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/phase1", summary="Phase 1 — open ticket analysis")
async def run_phase1(req: Phase1Request):
    """
    Called when a technician opens a ticket.
    Returns the three-pillar validation spec and initial KB matches so the
    technician can start SSH recon immediately.
    """
    try:
        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = agent.run_ticket_phase1(ticket, req.technician_id)
        _phase1_store[req.ticket_id] = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phase2", summary="Phase 2 — hypothesis generation")
async def run_phase2(req: Phase2Request):
    """
    Called after SSH recon and pillar baseline collection.
    Returns ranked fix hypotheses (trust-calibrated, safety-checked).
    Phase 1 must have been called first for this ticket.
    """
    phase1 = _phase1_store.get(req.ticket_id)
    if phase1 is None:
        raise HTTPException(
            status_code=400,
            detail=f"Phase 1 not run for ticket {req.ticket_id}. Call /phase1 first.",
        )
    try:
        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = agent.run_ticket_phase2(
            ticket=ticket,
            recon_output=req.recon_output,
            pillar_baseline_results=req.pillar_baseline,
            technician_id=req.technician_id,
            phase1_result=phase1,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete", summary="Complete ticket — validate, draft ERP, write KB")
async def complete_ticket(req: CompleteRequest):
    """
    Closes a ticket:
    1. Validates before/after pillar results.
    2. Drafts the ERP activity record (secrets scrubbed).
    3. Writes a new knowledge-base entry for future matching.
    4. Records technician command decisions for trust calibration.

    Phase 2 must have been called first for this ticket.
    """
    try:
        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = agent.complete_ticket(
            ticket=ticket,
            chosen_hypothesis_index=req.chosen_hypothesis_index,
            pillar_after_results=req.pillar_after_results,
            executed_steps=req.executed_steps,
            technician_id=req.technician_id,
            technician_notes=req.technician_notes,
            resolution_time_minutes=req.resolution_time_minutes,
            command_decisions=req.command_decisions,
        )
        _phase1_store.pop(req.ticket_id, None)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
