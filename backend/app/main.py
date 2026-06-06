from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import tickets, agent, activities

load_dotenv()

app = FastAPI(title="HERMIT API", version="0.1")

# Open CORS for local dev so your React app can call this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

@app.get("/health")
def health():
    return {"status": "ok", "service": "HERMIT API"}


# TODO: add your routes. A typical shape (yours may differ):
#   GET  /api/tickets              -> list tickets (via your Phoenix client)
#   GET  /api/tickets/{id}         -> ticket + customer system
#   POST /api/runs                 -> start an agent troubleshooting run
#   POST /api/runs/{id}/approve    -> run the approved command over SSH
#   POST /api/runs/{id}/activity   -> submit the activity to the ERP

app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
