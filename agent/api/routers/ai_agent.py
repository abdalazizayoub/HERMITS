"""
AI agent endpoints — the two-phase troubleshooting workflow.

POST /api/agent/ai/phase1          — open ticket → pillar spec + KB pre-match + real pillar baseline
POST /api/agent/ai/phase2          — post-recon  → ranked hypotheses + safety checks
POST /api/agent/ai/complete        — close ticket → pillar validation + ERP draft + KB write
POST /api/agent/ai/phase1/start    — start async phase1, returns job_id
GET  /api/agent/ai/phase1/status/{job_id} — SSE stream of phase1 progress/result
POST /api/agent/ai/phase2/start    — start async phase2, returns job_id
GET  /api/agent/ai/phase2/status/{job_id} — SSE stream of phase2 progress/result
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from components.models.pillar import PillarResult
from api.dependencies import get_agent
from api.utils import fetch_ticket_from_erp

router = APIRouter()

# In-memory store: ticket_id → {"phase1_result": Phase1Result, "pillar_baseline": PillarResult}
_phase1_store: dict[int, dict] = {}

# SSE job queues: job_id → asyncio.Queue holding the result or exception
_job_queues: dict[str, asyncio.Queue] = {}


# ── Request models ─────────────────────────────────────────────────────────────

class Phase1Request(BaseModel):
    ticket_id: int
    technician_id: str = "default"


class Phase2Request(BaseModel):
    ticket_id: int
    technician_id: str = "default"
    recon_output: Optional[dict] = None
    pillar_baseline: Optional[PillarResult] = None


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
    Returns the three-pillar validation spec, initial KB matches, and real
    pillar baseline captured over SSH so the technician can start recon immediately.
    """
    try:
        from erp.client import get_customer_system
        from ssh.runner import run_command, get_key_path

        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = agent.run_ticket_phase1(ticket, req.technician_id)

        # Fetch SSH details and capture real pillar baseline
        system_data = await get_customer_system(ticket_id=req.ticket_id)
        system = system_data["system"]
        host = system["ip"]
        port = system.get("port", 22)
        username = system["username"]
        key_path = get_key_path(req.ticket_id)

        spec = result.pillar_spec
        service_state_out = functional_impact_out = durability_out = ""
        if spec:
            svc = await run_command(host, port, username, key_path, spec.service_state_cmd)
            func = await run_command(host, port, username, key_path, spec.functional_impact_cmd)
            dur = await run_command(host, port, username, key_path, spec.durability_cmd)
            service_state_out = svc.get("stdout", "") or svc.get("stderr", "")
            functional_impact_out = func.get("stdout", "") or func.get("stderr", "")
            durability_out = dur.get("stdout", "") or dur.get("stderr", "")

        pillar_baseline = PillarResult(
            service_state_output=service_state_out,
            functional_impact_output=functional_impact_out,
            durability_output=durability_out,
        )

        _phase1_store[req.ticket_id] = {
            "phase1_result": result,
            "pillar_baseline": pillar_baseline,
        }

        return {**result.model_dump(), "pillar_baseline": pillar_baseline.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phase2", summary="Phase 2 — hypothesis generation")
async def run_phase2(req: Phase2Request):
    """
    Called after SSH recon. recon_output and pillar_baseline are optional —
    if omitted they are pulled from the backend session store and phase1 store
    respectively. Phase 1 must have been called first for this ticket.
    """
    stored = _phase1_store.get(req.ticket_id)
    if stored is None:
        raise HTTPException(
            status_code=400,
            detail=f"Phase 1 not run for ticket {req.ticket_id}. Call /phase1 first.",
        )

    phase1 = stored["phase1_result"]
    pillar_baseline = req.pillar_baseline or stored.get("pillar_baseline") or PillarResult(
        service_state_output="",
        functional_impact_output="",
        durability_output="",
    )

    recon_output = req.recon_output
    if not recon_output:
        from servers.routers.agent import _sessions as backend_sessions
        backend_session = backend_sessions.get(req.ticket_id)
        if backend_session:
            recon_output = backend_session.get("recon_adapted", {})
        else:
            recon_output = {}

    try:
        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = agent.run_ticket_phase2(
            ticket=ticket,
            recon_output=recon_output,
            pillar_baseline_results=pillar_baseline,
            technician_id=req.technician_id,
            phase1_result=phase1,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SSE streaming helpers ──────────────────────────────────────────────────────

async def _run_phase1_job(job_id: str, req: Phase1Request) -> None:
    """Run phase1 in a thread and push the result (or error) into the job queue."""
    q = _job_queues.get(job_id)
    if q is None:
        return
    try:
        from erp.client import get_customer_system
        from ssh.runner import run_command, get_key_path

        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: agent.run_ticket_phase1(ticket, req.technician_id)
        )

        system_data = await get_customer_system(ticket_id=req.ticket_id)
        system = system_data["system"]
        host = system["ip"]
        port = system.get("port", 22)
        username = system["username"]
        key_path = get_key_path(req.ticket_id)

        spec = result.pillar_spec
        service_state_out = functional_impact_out = durability_out = ""
        if spec:
            svc = await run_command(host, port, username, key_path, spec.service_state_cmd)
            func = await run_command(host, port, username, key_path, spec.functional_impact_cmd)
            dur = await run_command(host, port, username, key_path, spec.durability_cmd)
            service_state_out = svc.get("stdout", "") or svc.get("stderr", "")
            functional_impact_out = func.get("stdout", "") or func.get("stderr", "")
            durability_out = dur.get("stdout", "") or dur.get("stderr", "")

        pillar_baseline = PillarResult(
            service_state_output=service_state_out,
            functional_impact_output=functional_impact_out,
            durability_output=durability_out,
        )

        _phase1_store[req.ticket_id] = {
            "phase1_result": result,
            "pillar_baseline": pillar_baseline,
        }

        payload = {**result.model_dump(), "pillar_baseline": pillar_baseline.model_dump()}
        await q.put({"ok": True, "data": payload})
    except Exception as e:
        await q.put({"ok": False, "error": str(e)})


async def _run_phase2_job(job_id: str, req: Phase2Request) -> None:
    """Run phase2 in a thread and push the result (or error) into the job queue."""
    q = _job_queues.get(job_id)
    if q is None:
        return
    try:
        stored = _phase1_store.get(req.ticket_id)
        if stored is None:
            await q.put({"ok": False, "error": f"Phase 1 not run for ticket {req.ticket_id}."})
            return

        phase1 = stored["phase1_result"]
        pillar_baseline = req.pillar_baseline or stored.get("pillar_baseline") or PillarResult(
            service_state_output="", functional_impact_output="", durability_output=""
        )
        recon_output = req.recon_output or {}

        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: agent.run_ticket_phase2(
                ticket=ticket,
                recon_output=recon_output,
                pillar_baseline_results=pillar_baseline,
                technician_id=req.technician_id,
                phase1_result=phase1,
            ),
        )
        await q.put({"ok": True, "data": result})
    except Exception as e:
        await q.put({"ok": False, "error": str(e)})


@router.post("/phase1/start", summary="Start async Phase 1 — returns job_id for SSE polling")
async def start_phase1_stream(req: Phase1Request, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _job_queues[job_id] = asyncio.Queue()
    background_tasks.add_task(_run_phase1_job, job_id, req)
    return {"job_id": job_id}


@router.get("/phase1/status/{job_id}", summary="SSE stream — Phase 1 progress and result")
async def stream_phase1_status(job_id: str):
    from sse_starlette.sse import EventSourceResponse

    if job_id not in _job_queues:
        raise HTTPException(status_code=404, detail="Job not found")

    async def generator():
        yield {"event": "status", "data": json.dumps({"status": "processing"})}
        q = _job_queues[job_id]
        payload = await q.get()
        _job_queues.pop(job_id, None)
        if payload["ok"]:
            data = payload["data"]
            if hasattr(data, "dict"):
                data = data.model_dump()
            yield {"event": "done", "data": json.dumps({"status": "done", "data": data})}
        else:
            yield {"event": "error", "data": json.dumps({"status": "error", "message": payload["error"]})}

    return EventSourceResponse(generator())


@router.post("/phase2/start", summary="Start async Phase 2 — returns job_id for SSE polling")
async def start_phase2_stream(req: Phase2Request, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _job_queues[job_id] = asyncio.Queue()
    background_tasks.add_task(_run_phase2_job, job_id, req)
    return {"job_id": job_id}


@router.get("/phase2/status/{job_id}", summary="SSE stream — Phase 2 progress and result")
async def stream_phase2_status(job_id: str):
    from sse_starlette.sse import EventSourceResponse

    if job_id not in _job_queues:
        raise HTTPException(status_code=404, detail="Job not found")

    async def generator():
        yield {"event": "status", "data": json.dumps({"status": "processing"})}
        q = _job_queues[job_id]
        payload = await q.get()
        _job_queues.pop(job_id, None)
        if payload["ok"]:
            data = payload["data"]
            if hasattr(data, "dict"):
                data = data.model_dump()
            yield {"event": "done", "data": json.dumps({"status": "done", "data": data})}
        else:
            yield {"event": "error", "data": json.dumps({"status": "error", "message": payload["error"]})}

    return EventSourceResponse(generator())


# ── Complete ───────────────────────────────────────────────────────────────────

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
        stored = _phase1_store.get(req.ticket_id)
        pillar_baseline = stored.get("pillar_baseline") if isinstance(stored, dict) else None

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
            pillar_baseline=pillar_baseline,
        )
        _phase1_store.pop(req.ticket_id, None)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
