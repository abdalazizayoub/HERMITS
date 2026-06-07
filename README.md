# HERMITS

Hybrid Engine for Remediation, Monitoring & IT Support

HERMITS is an AI-assisted incident response platform built for the START Vienna Hackathon. It combines a mock Phoenix ERP ticketing workflow, SSH-based customer system reconnaissance, agent-driven hypothesis generation, and approval-guarded remediation.

The system is designed around a human-in-the-loop process:

- AI proposes diagnostics, validation pillars, and remediation steps.
- The technician approves each system action before execution.
- Every action is audited and persisted.
- Resolved incidents are turned into ERP activity reports and knowledge base entries.

## What is included

- `server.py` — unified FastAPI backend combining infrastructure and AI agent routes.
- `docker-compose.yml` — runs the API server and the static technician UI.
- `ui.html` — built-in static dashboard served by nginx.
- `frontend/` — optional React/Vite dashboard source for local frontend development.
- `hermits_cli.py` — interactive end-to-end incident response CLI.
- `backend/` — ERP, SSH, activity submission, and audit infrastructure.
- `agent/` — AI workflows, Gemini integration, KB matching, and voice summarization.
- `keys/` — SSH private keys used for customer VM access.
- `data/` — local storage for KB, memory context, and runtime data.
- `audit_logs/` — detailed ticket audit trails.

## Core workflow

1. `GET /api/tickets/` — list open tickets.
2. `GET /api/tickets/{id}` — ticket details and SSH connection metadata.
3. `POST /api/agent/ai/phase1` — generate pillar validation commands and KB context.
4. `POST /api/agent/recon` — run SSH reconnaissance on the target VM.
5. `POST /api/agent/ai/phase2` — generate ranked hypotheses and approved fix steps.
6. `POST /api/agent/execute` — execute one approved SSH command.
7. `POST /api/agent/validate` — validate the fix using public test scripts.
8. `POST /api/agent/ai/complete` — draft ERP activity and store knowledge base entries.
9. `POST /api/activities/submit` — submit the completed activity to the ERP and mark the ticket done.

## Prerequisites

- Python 3.11+ (or compatible Python 3.x)
- Docker and Docker Compose
- Optional: Node.js 18+ for `frontend/` development
- Valid AI credentials for Gemini and ElevenLabs for full agent/voice behavior

## Setup

### Docker Compose

From the repository root:

```bash
docker compose up --build
```

This starts:

- API server on `http://localhost:8080`
- UI on `http://localhost:5173`

### Local Python setup

Install the Python dependencies:

```bash
python -m pip install -r backend/requirements.txt -r agent/requirements.txt
python -m pip install httpx
```

Create or update `.env` with your local values. The project loads `.env` automatically via `python-dotenv`.

## Recommended environment variables

- `GEMINI_API_KEY` — Google Gemini API key.
- `ELEVENLABS_API_KEY` — ElevenLabs API key.
- `ELEVENLABS_VOICE_ID` — ElevenLabs voice name or ID (default: `Rachel`).
- `SSH_KEY_DIR` — directory containing SSH keys (default: `./keys`).
- `SSH_USERNAME` — SSH username for target VMs (default: `azureuser`).
- `SSH_TIMEOUT` — SSH connection timeout in seconds.
- `SSH_COMMAND_TIMEOUT` — standard command timeout in seconds.
- `SSH_VALIDATION_TIMEOUT` — validation command timeout in seconds.
- `HERMITS_DATA_DIR` — local data directory (default: `./data`).
- `PHOENIX_API_BASE_URL` / `PHOENIX_API_TOKEN` — mock ERP endpoint and token.

## Run the server

Run locally with:

```bash
python server.py
```

Or with uvicorn:

```bash
uvicorn server:app --reload --port 8080
```

## Built-in UI

If Docker Compose is running, open:

```text
http://localhost:5173
```

If you do not use Docker Compose, serve `ui.html` from a local web server and point it at the API.

## Frontend development

The `frontend/` folder contains a React + Vite dashboard. To develop locally:

```bash
cd frontend
npm install
npm run dev
```

Build for production:

```bash
npm run build
```

## CLI usage

The CLI provides an interactive ticket workflow:

```bash
python hermits_cli.py <ticket_id>
python hermits_cli.py <ticket_id> --server http://localhost:8080
python hermits_cli.py <ticket_id> --technician alice
python hermits_cli.py <ticket_id> --dry-run
```

## Testing

Run tests with pytest from the repository root:

```bash
pytest -q
```

The AI and voice components are mocked in tests, so no API keys are required.

## Project structure

- `server.py` — unified startup for HERMITS API.
- `backend/` — infrastructure for ERP, SSH, activities, and audit logs.
- `agent/` — AI routes, Gemini orchestration, KB, and voice features.
- `keys/` — SSH key material for ticket VMs.
- `data/` — knowledge base and memory context storage.
- `audit_logs/` — audit trail JSONL files.
- `frontend/` — optional React dashboard source.

## Notes

- Every SSH command must be approved by the technician.
- The safety layer blocks unsafe commands and only allows one approved command per execute request.
- Resolved incidents are appended to `data/knowledge_base.jsonl`.
- Audit logs are stored in `audit_logs/` for traceability.

## Additional documentation

For deeper AI/agent details and voice features, see `agent/README.md`.
