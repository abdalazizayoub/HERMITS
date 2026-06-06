"""
Triage-poller control endpoints.

GET  /api/agent/ai/triage/status  — is the poller running?
POST /api/agent/ai/triage/start   — start the background poller
POST /api/agent/ai/triage/stop    — stop the background poller
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from api.dependencies import get_agent, get_triage_poller, set_triage_poller

logger = logging.getLogger("hermits.api.triage")
router = APIRouter()


def _is_running(poller) -> bool:
    return poller is not None and poller._thread is not None and poller._thread.is_alive()


# ── ERP adapter ────────────────────────────────────────────────────────────────

class _ERPAdapter:
    """
    Synchronous wrapper around the async backend ERP client.
    Used by TriagePoller which runs in a background thread (no running event loop).
    """

    def list_open_tickets(self):
        from app.erp import client as erp
        from components.models.ticket import Ticket

        async def _fetch():
            raw = await erp.list_tickets(status="OPEN")
            tickets_data = raw if isinstance(raw, list) else raw.get("tickets", [])
            result = []
            for t in tickets_data:
                try:
                    result.append(Ticket(**t))
                except Exception as exc:
                    logger.warning("Skipping malformed ticket: %s", exc)
            return result

        return asyncio.run(_fetch())

    def get_ticket(self, ticket_id: int):
        from app.erp import client as erp
        from components.models.ticket import Ticket

        async def _fetch():
            raw = await erp.get_ticket(ticket_id)
            return Ticket(**raw)

        return asyncio.run(_fetch())


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/status", summary="Triage poller status")
def triage_status():
    poller = get_triage_poller()
    running = _is_running(poller)
    return {
        "running": running,
        "poll_interval_seconds": poller.POLL_INTERVAL_SECONDS if poller else None,
        "prewarm_top_n": poller.PREWARM_TOP_N if poller else None,
    }


@router.post("/start", summary="Start the background triage poller")
def start_triage():
    """
    Starts a background thread that polls the ERP every TRIAGE_POLL_INTERVAL_SECONDS
    seconds, scores open tickets for urgency (via Gemini), and pre-warms the top-N
    tickets through Phase 1 so technicians get instant responses.
    """
    from components.triage.poller import TriagePoller

    poller = get_triage_poller()

    if _is_running(poller):
        return {"message": "Triage poller is already running"}

    if poller is None:
        poller = TriagePoller(erp_client=_ERPAdapter(), agent=get_agent())
        set_triage_poller(poller)

    poller.start()
    return {"message": "Triage poller started"}


@router.post("/stop", summary="Stop the background triage poller")
def stop_triage():
    poller = get_triage_poller()
    if not _is_running(poller):
        return {"message": "Triage poller is not running"}
    poller.stop()
    return {"message": "Triage poller stopped"}
