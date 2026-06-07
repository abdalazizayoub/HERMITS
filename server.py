"""
HERMITS — combined server entry point.

Adds both sub-packages to sys.path so their internal imports resolve, then
builds ONE FastAPI app that includes:

  Backend infrastructure routes  (SSH recon/execute/validate, ERP tickets,
                                   ERP activity submission, audit log)
  Agent AI routes                (Phase 1/2 workflow, KB queries, voice,
                                   triage poller control)

Run:
    uvicorn server:app --reload --port 8080
or:
    python server.py
"""
import os
import sys

# ── Path setup — must come before any project imports ─────────────────────────
_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, "backend"))          # exposes: servers.*
sys.path.insert(0, os.path.join(_root, "backend", "servers"))  # exposes: erp, ssh, routers, audit_logs
sys.path.insert(0, os.path.join(_root, "agent"))            # exposes: components.*, api.*

# ── Standard library / third-party ────────────────────────────────────────────
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# ── Backend routers (untouched — imported, not modified) ──────────────────────
from servers.routers import tickets as tickets_router
from servers.routers import agent as backend_agent_router
from servers.routers import activities as activities_router

# ── Agent AI routers (new — live in agent/api/routers/) ───────────────────────
from api.routers import ai_agent as ai_agent_router
from api.routers import voice as voice_router
from api.routers import knowledge_base as kb_router
from api.routers import triage as triage_router

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="HERMITS API",
    version="1.0",
    description=(
        "AI-assisted incident response system. "
        "Backend infrastructure routes + Agent AI routes in one server."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "HERMITS API"}


# ── Backend infrastructure routes ──────────────────────────────────────────────
#   GET/PATCH /api/tickets/...
app.include_router(tickets_router.router, prefix="/api/tickets", tags=["tickets"])

#   POST /api/agent/recon|execute|validate
#   GET  /api/agent/audit/{ticket_id}
app.include_router(backend_agent_router.router, prefix="/api/agent", tags=["agent-infra"])

#   POST /api/activities/submit
app.include_router(activities_router.router, prefix="/api/activities", tags=["activities"])

# ── Agent AI routes ────────────────────────────────────────────────────────────
#   POST /api/agent/ai/phase1
#   POST /api/agent/ai/phase2
#   POST /api/agent/ai/complete
app.include_router(ai_agent_router.router, prefix="/api/agent/ai", tags=["ai-agent"])

#   GET  /api/agent/ai/voice/summary/{ticket_id}
#   POST /api/agent/ai/voice/digest
#   POST /api/agent/ai/voice/digest/audio
app.include_router(voice_router.router, prefix="/api/agent/ai/voice", tags=["ai-voice"])

#   GET  /api/agent/ai/kb/entries
#   GET  /api/agent/ai/kb/entries/{entry_id}
#   POST /api/agent/ai/kb/match
app.include_router(kb_router.router, prefix="/api/agent/ai/kb", tags=["ai-knowledge-base"])

#   GET  /api/agent/ai/triage/status
#   POST /api/agent/ai/triage/start
#   POST /api/agent/ai/triage/stop
app.include_router(triage_router.router, prefix="/api/agent/ai/triage", tags=["ai-triage"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
