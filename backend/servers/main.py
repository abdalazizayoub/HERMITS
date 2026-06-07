import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import tickets, agent, activities

load_dotenv()

logger = logging.getLogger("hermits.main")


# ── Sync ERP adapter for the TriagePoller (runs in a background thread) ────────

class _SyncERPAdapter:
    """
    Wraps the async ERP client so the TriagePoller (which lives in a
    non-async background thread) can call it synchronously.
    """
    def list_open_tickets(self):
        from erp import client as erp
        from components.models.ticket import Ticket as AgentTicket

        try:
            raw_list = asyncio.run(erp.list_tickets(status="OPEN"))
            tickets_data = raw_list if isinstance(raw_list, list) else raw_list.get("tickets", [])
            result = []
            for t in tickets_data:
                try:
                    result.append(AgentTicket(**t))
                except Exception:
                    pass
            return result
        except Exception as exc:
            logger.warning("SyncERPAdapter.list_open_tickets failed: %s", exc)
            return []

    def get_ticket(self, ticket_id: int):
        from erp import client as erp
        from components.models.ticket import Ticket as AgentTicket
        data = asyncio.run(erp.get_ticket(ticket_id))
        return AgentTicket(**data)


# ── Lifespan: start/stop the TriagePoller ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    poller = None
    try:
        from components.triage.poller import TriagePoller
        from api.dependencies import set_triage_poller
        poller = TriagePoller(erp_client=_SyncERPAdapter())
        set_triage_poller(poller)
        poller.start()
        logger.info("TriagePoller started")
    except Exception as exc:
        logger.warning("TriagePoller failed to start: %s", exc)

    yield

    if poller is not None:
        poller.stop()
        logger.info("TriagePoller stopped")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="HERMIT API", version="0.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "HERMIT API"}


app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
