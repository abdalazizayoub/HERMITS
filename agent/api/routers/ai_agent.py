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
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from components.gemini_client import GeminiParseError
from components.models.pillar import PillarResult
from api.dependencies import get_agent
from api.utils import fetch_ticket_from_erp

router = APIRouter()
logger = logging.getLogger("hermits.ai_agent")

# ── Session persistence ────────────────────────────────────────────────────────

SESSION_DIR = Path("/tmp/hermits_sessions")
SESSION_DIR.mkdir(exist_ok=True)


def _save_phase1(ticket_id: int, entry: dict) -> None:
    try:
        saveable = {}
        for k, v in entry.items():
            if hasattr(v, "model_dump"):
                saveable[k] = v.model_dump(mode="json")
            else:
                saveable[k] = v
        (SESSION_DIR / f"phase1_{ticket_id}.json").write_text(
            json.dumps(saveable, default=str)
        )
    except Exception as exc:
        logger.warning("Failed to persist phase1 for ticket %d: %s", ticket_id, exc)


def _load_phase1(ticket_id: int) -> dict | None:
    try:
        f = SESSION_DIR / f"phase1_{ticket_id}.json"
        if not f.exists():
            return None
        raw = json.loads(f.read_text())
        from components.services.runner import Phase1Result
        from components.models.ticket import Ticket
        result: dict = {}
        if "pillar_baseline" in raw and raw["pillar_baseline"]:
            result["pillar_baseline"] = PillarResult.model_validate(raw["pillar_baseline"])
        if "ticket" in raw and raw["ticket"]:
            result["ticket"] = Ticket.model_validate(raw["ticket"])
        if "phase1_result" in raw and raw["phase1_result"]:
            try:
                result["phase1_result"] = Phase1Result.model_validate(raw["phase1_result"])
            except Exception:
                result["phase1_result"] = None
        return result or None
    except Exception as exc:
        logger.warning("Failed to load phase1 for ticket %d: %s", ticket_id, exc)
        return None


# ── In-memory store (backed by files above) ────────────────────────────────────

_phase1_store: dict[int, dict] = {}

# SSE job queues: job_id → asyncio.Queue holding the result or exception
_job_queues: dict[str, asyncio.Queue] = {}


# ── Frontend-schema transformers ───────────────────────────────────────────────

def _kb_match_to_frontend(m) -> dict:
    """Flatten nested KBMatch/KBEntry into the shape the frontend KBMatch type expects."""
    e = m.entry
    return {
        "entry_id": e.id,
        "similarity_score": m.similarity_score,
        "confidence_boost": m.confidence_boost,
        "root_cause": e.root_cause,
        "fix_commands": e.fix_commands,
        "resolution_time_minutes": e.resolution_time_minutes,
        "service_hint": (e.ticket_fingerprint.service_hint if e.ticket_fingerprint else None),
        "validation_passed": e.validation_passed,
    }


def _phase1_to_frontend(result, pillar_baseline) -> dict:
    """Map backend Phase1Result + PillarResult → shape the frontend Phase1Result type expects."""
    return {
        "pillar_spec": result.pillar_spec.model_dump() if result.pillar_spec else None,
        "kb_matches": [_kb_match_to_frontend(m) for m in result.kb_matches_initial],
        "memory_context": result.memory_context,
        "cache_hit": result.cache_hit,
        "pillar_baseline": pillar_baseline.model_dump() if pillar_baseline else None,
    }


def _phase2_to_frontend(result) -> dict:
    """Map backend AgentRunResult → shape the frontend Phase2Result type expects."""
    return {
        "hypothesis": result.best_hypothesis.hypothesis.model_dump(),
        "safety_results": [
            {"is_safe": s.safe, "reason": s.reason, "warnings": []}
            for s in result.safety_checks
        ],
        "pillar_spec": result.pillar_spec.model_dump() if result.pillar_spec else None,
        "recon_summary": result.best_hypothesis.selection_rationale or "",
        "all_hypotheses": [],
    }


# ── Request models ─────────────────────────────────────────────────────────────

class Phase1Request(BaseModel):
    ticket_id: int
    technician_id: str = "default"
    force_refresh: bool = False  # re-analyze: skip prewarm cache, generate fresh


class Phase2Request(BaseModel):
    ticket_id: int
    technician_id: str = "default"
    recon_output: Optional[dict] = None
    pillar_baseline: Optional[PillarResult] = None
    failure_context: Optional[str] = None


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
    try:
        from erp.client import get_customer_system
        from ssh.runner import run_pillar_baseline, get_key_path

        ticket = await fetch_ticket_from_erp(req.ticket_id)
        agent = get_agent()
        result = agent.run_ticket_phase1(ticket, req.technician_id, force_refresh=req.force_refresh)

        system_data = await get_customer_system(ticket_id=req.ticket_id)
        system = system_data["system"]
        host = system["ip"]
        port = system.get("port", 22)
        username = system["username"]
        key_path = get_key_path(req.ticket_id)

        spec = result.pillar_spec
        service_state_out = functional_impact_out = durability_out = ""
        if spec:
            svc, func, dur = await asyncio.gather(
                run_command(host, port, username, key_path, spec.service_state_cmd),
                run_command(host, port, username, key_path, spec.functional_impact_cmd),
                run_command(host, port, username, key_path, spec.durability_cmd),
            )
            service_state_out = svc.get("stdout", "") or svc.get("stderr", "")
            functional_impact_out = func.get("stdout", "") or func.get("stderr", "")
            durability_out = dur.get("stdout", "") or dur.get("stderr", "")

        pillar_baseline = PillarResult(
            service_state_output=service_state_out,
            functional_impact_output=functional_impact_out,
            durability_output=durability_out,
        )

        entry = {
            "phase1_result": result,
            "pillar_baseline": pillar_baseline,
            "ticket": ticket,
        }
        _phase1_store[req.ticket_id] = entry
        _save_phase1(req.ticket_id, entry)

        return {**result.model_dump(), "pillar_baseline": pillar_baseline.model_dump()}
    except GeminiParseError as e:
        raise HTTPException(status_code=503, detail=f"LLM temporarily unavailable, retry in 10s: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phase2", summary="Phase 2 — hypothesis generation")
async def run_phase2(req: Phase2Request):
    stored = _phase1_store.get(req.ticket_id)
    if stored is None:
        stored = _load_phase1(req.ticket_id)
        if stored is not None:
            _phase1_store[req.ticket_id] = stored  # repopulate memory cache
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Phase 1 not run for ticket {req.ticket_id}. Call /phase1 first.",
            )

    phase1 = stored.get("phase1_result")
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
            # Try loading from persisted session file
            try:
                sf = SESSION_DIR / f"session_{req.ticket_id}.json"
                if sf.exists():
                    sess = json.loads(sf.read_text())
                    recon_output = sess.get("recon_adapted", {})
                else:
                    recon_output = {}
            except Exception:
                recon_output = {}

    try:
        cached_ticket = stored.get("ticket")
        if cached_ticket is not None:
            ticket = cached_ticket
        else:
            ticket = await fetch_ticket_from_erp(req.ticket_id)

        agent = get_agent()
        result = agent.run_ticket_phase2(
            ticket=ticket,
            recon_output=recon_output,
            pillar_baseline_results=pillar_baseline,
            technician_id=req.technician_id,
            phase1_result=phase1,
            failure_context=req.failure_context or "",
        )
        return _phase2_to_frontend(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SSE streaming helpers ──────────────────────────────────────────────────────

async def _run_phase1_job(job_id: str, req: Phase1Request) -> None:
    q = _job_queues.get(job_id)
    if q is None:
        return
    try:
        from erp.client import get_customer_system
        from ssh.runner import run_pillar_baseline, get_key_path

        # Fetch ticket and SSH system info in parallel — both are network calls
        ticket, system_data = await asyncio.gather(
            fetch_ticket_from_erp(req.ticket_id),
            get_customer_system(ticket_id=req.ticket_id),
        )
        agent = get_agent()
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: agent.run_ticket_phase1(ticket, req.technician_id, force_refresh=req.force_refresh)
        )

        system = system_data["system"]
        host = system["ip"]
        port = system.get("port", 22)
        username = system["username"]
        key_path = get_key_path(req.ticket_id)

        spec = result.pillar_spec
        service_state_out = functional_impact_out = durability_out = ""
        if spec:
            svc, func, dur = await run_pillar_baseline(
                host, port, username, key_path,
                spec.service_state_cmd, spec.functional_impact_cmd, spec.durability_cmd,
            )
            service_state_out = svc.get("stdout", "") or svc.get("stderr", "")
            functional_impact_out = func.get("stdout", "") or func.get("stderr", "")
            durability_out = dur.get("stdout", "") or dur.get("stderr", "")

        pillar_baseline = PillarResult(
            service_state_output=service_state_out,
            functional_impact_output=functional_impact_out,
            durability_output=durability_out,
        )

        entry = {
            "phase1_result": result,
            "pillar_baseline": pillar_baseline,
        }
        _phase1_store[req.ticket_id] = entry
        _save_phase1(req.ticket_id, entry)

        payload = _phase1_to_frontend(result, pillar_baseline)
        await q.put({"ok": True, "data": payload})
    except Exception as e:
        await q.put({"ok": False, "error": str(e)})


async def _run_phase2_job(job_id: str, req: Phase2Request) -> None:
    q = _job_queues.get(job_id)
    if q is None:
        return
    try:
        stored = _phase1_store.get(req.ticket_id) or _load_phase1(req.ticket_id)
        if stored is None:
            await q.put({"ok": False, "error": f"Phase 1 not run for ticket {req.ticket_id}."})
            return

        phase1 = stored.get("phase1_result")
        pillar_baseline = req.pillar_baseline or stored.get("pillar_baseline") or PillarResult(
            service_state_output="", functional_impact_output="", durability_output=""
        )
        recon_output = req.recon_output or {}

        ticket = stored.get("ticket") or await fetch_ticket_from_erp(req.ticket_id)
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
        await q.put({"ok": True, "data": _phase2_to_frontend(result)})
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
            if hasattr(data, "model_dump"):
                data = data.model_dump()
            yield {"event": "done", "data": json.dumps({"status": "done", "data": data}, default=str)}
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
            if hasattr(data, "model_dump"):
                data = data.model_dump()
            yield {"event": "done", "data": json.dumps({"status": "done", "data": data}, default=str)}
        else:
            yield {"event": "error", "data": json.dumps({"status": "error", "message": payload["error"]})}

    return EventSourceResponse(generator())


# ── Complete ───────────────────────────────────────────────────────────────────

@router.post("/complete", summary="Complete ticket — validate, draft ERP, write KB")
async def complete_ticket(req: CompleteRequest):
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
        # Clean up persisted session files
        for fname in [f"phase1_{req.ticket_id}.json", f"session_{req.ticket_id}.json"]:
            try:
                (SESSION_DIR / fname).unlink(missing_ok=True)
            except Exception:
                pass
        return result
    except GeminiParseError as e:
        raise HTTPException(status_code=503, detail=f"LLM temporarily unavailable, retry in 10s: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
