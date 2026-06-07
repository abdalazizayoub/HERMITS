import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from erp import client as erp
import httpx

from api.dependencies import get_agent
from api.utils import fetch_ticket_from_erp
from components.models.pillar import PillarResult
from ssh.runner import get_key_path, run_command

router = APIRouter()

# Cache of completed pipeline results keyed by ticket_id.
# Populated by background tasks so subsequent opens are instant.
_pipeline_cache: dict[int, dict] = {}
_pipeline_running: set[int] = set()

# How long to wait for the pipeline before returning the ticket without it.
# Frontend falls back to live SSE flow when auto_pipeline is None.
_PIPELINE_TIMEOUT_SECONDS = 45


@router.get("/")
async def list_tickets(status: str = "", priority: str = ""):
    try:
        tickets = await erp.list_tickets(status=status, priority=priority)
        return {"tickets": tickets}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    auto_run_pipeline: bool = True,
    background_tasks: BackgroundTasks = None,
):
    try:
        ticket = await fetch_ticket_from_erp(ticket_id=ticket_id)
        system_data = await erp.get_customer_system(ticket_id=ticket_id)
        system = system_data.get("system", {})

        payload = {"ticket": ticket.model_dump(), "system": system}

        if auto_run_pipeline:
            # If a previous background run finished, return it immediately.
            if ticket_id in _pipeline_cache:
                payload["auto_pipeline"] = _pipeline_cache[ticket_id]

            elif ticket_id not in _pipeline_running:
                # Try to compute it within the timeout window.
                # If it finishes in time, great — the frontend gets it now.
                # If it times out, it continues as a background task and the
                # frontend uses the live SSE flow instead.
                try:
                    result = await asyncio.wait_for(
                        _run_ticket_pipeline(ticket, system),
                        timeout=_PIPELINE_TIMEOUT_SECONDS,
                    )
                    _pipeline_cache[ticket_id] = result
                    payload["auto_pipeline"] = result
                except asyncio.TimeoutError:
                    # Kick off in background so it's ready next time.
                    if background_tasks is not None:
                        background_tasks.add_task(
                            _run_and_cache_pipeline, ticket_id, ticket, system
                        )
                    payload["auto_pipeline"] = {
                        "success": False,
                        "error": "Pipeline timed out — using live flow",
                    }
            else:
                # Already running in background — return None so frontend uses SSE.
                payload["auto_pipeline"] = None

        return payload

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


async def _run_and_cache_pipeline(ticket_id: int, ticket, system: dict) -> None:
    """Background task: run pipeline and store result in cache."""
    _pipeline_running.add(ticket_id)
    try:
        result = await _run_ticket_pipeline(ticket, system)
        _pipeline_cache[ticket_id] = result
    except Exception:
        pass
    finally:
        _pipeline_running.discard(ticket_id)


async def _run_ticket_pipeline(ticket, system: dict) -> dict:
    agent = get_agent()
    try:
        # Phase 1: pillar spec + KB matches (uses cache if pre-warmed by TriagePoller)
        phase1_result = agent.run_ticket_phase1(ticket, technician_id="system")

        host = system.get("ip")
        port = system.get("port", 22)
        username = system.get("username")
        key_path = get_key_path(ticket.id)

        pillar_baseline = PillarResult(
            service_state_output="",
            functional_impact_output="",
            durability_output="",
        )

        spec = phase1_result.pillar_spec
        if spec and host and username:
            try:
                service_state, functional_impact, durability = await asyncio.gather(
                    run_command(host, port, username, key_path, spec.service_state_cmd),
                    run_command(host, port, username, key_path, spec.functional_impact_cmd),
                    run_command(host, port, username, key_path, spec.durability_cmd),
                )
                pillar_baseline = PillarResult(
                    service_state_output=service_state.get("stdout", "") or service_state.get("stderr", ""),
                    functional_impact_output=functional_impact.get("stdout", "") or functional_impact.get("stderr", ""),
                    durability_output=durability.get("stdout", "") or durability.get("stderr", ""),
                )
            except Exception:
                pass  # Proceed with empty baseline; Phase 2 can still run

        # Phase 2: hypothesis generation
        run_result = agent.run_ticket_phase2(
            ticket=ticket,
            recon_output={},
            pillar_baseline_results=pillar_baseline,
            technician_id="system",
            phase1_result=phase1_result,
            failure_context="auto pipeline run on ticket open",
        )

        # Transform to the schema the frontend Phase1Result / Phase2Result types expect
        def _kb_flat(m):
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

        phase1_fe = {
            "pillar_spec": phase1_result.pillar_spec.model_dump() if phase1_result.pillar_spec else None,
            "kb_matches": [_kb_flat(m) for m in phase1_result.kb_matches_initial],
            "memory_context": phase1_result.memory_context,
            "cache_hit": phase1_result.cache_hit,
            "pillar_baseline": pillar_baseline.model_dump(),
        }
        phase2_fe = {
            "hypothesis": run_result.best_hypothesis.hypothesis.model_dump(),
            "safety_results": [
                {"is_safe": s.safe, "reason": s.reason, "warnings": []}
                for s in run_result.safety_checks
            ],
            "pillar_spec": run_result.pillar_spec.model_dump() if run_result.pillar_spec else None,
            "recon_summary": run_result.best_hypothesis.selection_rationale or "",
            "all_hypotheses": [],
        }
        return {
            "success": True,
            "phase1": phase1_fe,
            "phase2": phase2_fe,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@router.patch("/{ticket_id}/status")
async def set_status(ticket_id: int, body: dict):
    if "status" not in body:
        raise HTTPException(status_code=400, detail="Missing 'status' in request body")
    # Invalidate cache when ticket is closed
    _pipeline_cache.pop(ticket_id, None)
    try:
        updated_ticket = await erp.patch_ticket_status(ticket_id=ticket_id, status=body["status"])
        return {"ticket": updated_ticket}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        raise HTTPException(status_code=502, detail=str(e))
