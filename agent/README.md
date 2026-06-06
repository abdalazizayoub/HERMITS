# HERMITS — AI-Assisted Sysadmin Incident Response System

HERMITS is an AI-powered backend for structured incident resolution. It ingests support tickets, runs recon analysis, generates diagnostic hypotheses using Gemini, validates fixes via three deterministic pillars, and produces ERP-ready activity reports — all while maintaining a growing knowledge base of past resolutions.

Built for the START Hack Vienna '26 techbold track, HERMITS pairs with a human technician: it proposes, the technician approves, and the system learns from every decision to improve future recommendations.

---

## Architecture

```
                        ┌─────────────────────────────────────────────────────┐
                        │                  HERMITS Backend                     │
                        │                                                       │
  Ticket (ERP)  ──────► │  TriagePoller ──► PrewarmCache                       │
                        │       │                 │                             │
                        │       ▼                 ▼                             │
  Recon data   ──────► │  HermitsAgent.run_ticket()                            │
  (SSH output)         │       │                                               │
                        │       ├──► ContextLoader (memory.md)                 │
                        │       ├──► KBMatcher (JSONL store)                   │
                        │       ├──► ThreePillarsGenerator (Gemini)            │
                        │       ├──► HypothesisGenerator (Gemini)              │
                        │       ├──► TrustCalibrator (pure Python)             │
                        │       └──► SafetyLayer (regex)                       │
                        │                                                       │
  Fix results  ──────► │  HermitsAgent.complete_ticket()                      │
                        │       ├──► PillarValidator (Gemini)                  │
                        │       ├──► ERPDrafter (Gemini)                       │
                        │       ├──► KBWriter → knowledge_base.jsonl           │
                        │       └──► AuditLog → audit_{date}.jsonl             │
                        │                                                       │
  Voice button ──────► │  TicketVoiceSummary / MonthlyDigest (ElevenLabs)    │
                        └─────────────────────────────────────────────────────┘
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in GEMINI_API_KEY and ELEVENLABS_API_KEY
```

---

## Ingest a policy PDF

```bash
python -m hermits.memory.pdf_ingestor path/to/policy.pdf
```

This writes the extracted text to `data/memory.md`, which is automatically loaded as context for all Gemini calls.

---

## Run tests

```bash
pytest tests/ -v
```

All Gemini and ElevenLabs calls are mocked — no API keys needed for tests.

---

## Start the background triage poller

```python
from hermits.triage.poller import TriagePoller
from your_erp_client import MyERPClient  # implements ERPClient protocol

poller = TriagePoller(erp_client=MyERPClient())
poller.start()   # call from FastAPI startup event
# ...
poller.stop()    # call from FastAPI shutdown event
```

Or as a standalone script (requires an ERPClient implementation):

```bash
python -m hermits.triage.poller
```

---

## Integration contract with Person A (SSH executor)

### `run_ticket(ticket, recon_output, pillar_baseline_results, technician_id) → AgentRunResult`

**Inputs:**
- `ticket: Ticket` — the ERP ticket object
- `recon_output: dict` — SSH recon results with keys:
  - `logs: list[str]` — last N log lines
  - `service_statuses: dict[str, str]` — service name → status string
  - `disk_usage: dict[str, {used_pct: float, inode_pct: float}]` — mount → usage
  - `processes: list[str]` — top process lines
  - `cron_timers: list[str]` — active cron/timer entries
- `pillar_baseline_results: PillarResult` — output of running pillar commands before any fix
- `technician_id: str` — technician identifier for trust calibration

**Output: `AgentRunResult`**
- `pillar_spec` — the 3 validation commands to run before and after fixes
- `hypothesis_set.hypotheses` — 3 ranked fix hypotheses (use index 0 first)
- `hypothesis.fix_steps` — ordered list of commands for the technician to approve/run
- `safety_checks` — per-step safety verdicts (block any where `safe=False`)
- `kb_matches` — similar past incidents for context

### `complete_ticket(ticket, chosen_hypothesis_index, pillar_after_results, executed_steps, technician_id, technician_notes, resolution_time_minutes, command_decisions) → CompletionResult`

**Inputs:**
- `chosen_hypothesis_index: int` — index into `hypothesis_set.hypotheses`
- `pillar_after_results: PillarResult` — output of pillar commands after the fix
- `executed_steps: list[dict]` — `{command, output, approved, timestamp}` for each step run
- `command_decisions: list[tuple[str, bool]]` — `(command, approved)` pairs for trust learning

**Output: `CompletionResult`**
- `validation_result` — per-pillar pass/fail with notes
- `activity` — ERP Activity object ready to submit to Phoenix
- `kb_entry_id` — ID of the new knowledge base entry
- `all_pillars_passed` — `True` if the incident is fully resolved

---

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | required |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | required |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice name or ID | `Rachel` |
| `HERMITS_DATA_DIR` | Path to data directory | `./data` |
| `TRIAGE_POLL_INTERVAL_SECONDS` | How often the poller checks for new tickets | `120` |
| `TRIAGE_PREWARM_TOP_N` | How many top-urgency tickets to pre-warm | `3` |
| `PREWARM_TTL_SECONDS` | Cache TTL in seconds | `900` |
| `ERP_BASE_URL` | Base URL for the ERP system | — |
| `ERP_BEARER_TOKEN` | Bearer token for ERP authentication | — |

---

## Module descriptions

| Module | Description |
|---|---|
| `hermits.agent.runner` | Main orchestrator: `HermitsAgent.run_ticket()` and `complete_ticket()` |
| `hermits.agent.three_pillars` | Generates 3 read-only validation commands via Gemini |
| `hermits.agent.hypothesis_generator` | Generates 3 ranked fix hypotheses via Gemini |
| `hermits.agent.pillar_validator` | Compares before/after pillar outputs via Gemini |
| `hermits.agent.erp_drafter` | Produces ERP activity fields via Gemini (secrets scrubbed) |
| `hermits.agent.trust_calibrator` | Reorders fix steps by technician approval history |
| `hermits.agent.safety` | Regex-based hard-block for destructive commands |
| `hermits.knowledge_base.store` | Append-only JSONL store with file locking |
| `hermits.knowledge_base.matcher` | Token-overlap similarity matching against KB |
| `hermits.knowledge_base.writer` | Extracts fingerprints and persists resolved incidents |
| `hermits.memory.pdf_ingestor` | Extracts text from policy PDFs into memory.md |
| `hermits.memory.context_loader` | Loads memory.md and truncates for Gemini context |
| `hermits.triage.poller` | Background thread that polls ERP and pre-warms cache |
| `hermits.triage.prewarm_cache` | In-memory TTL cache for pre-warmed run results |
| `hermits.voice.ticket_summary` | On-demand ElevenLabs MP3 summary per ticket |
| `hermits.voice.monthly_digest` | Monthly voice + text digest via Gemini + ElevenLabs |
| `hermits.gemini_client` | Shared Gemini wrapper with retry and JSON parsing |
| `hermits.audit_log` | Append-only JSONL command and event audit trail |

---

## Troubleshooting

**`GeminiParseError: Failed to parse Gemini JSON response`**
Gemini returned markdown or prose instead of JSON. This is retried automatically twice. If it persists, add a more explicit instruction to the system prompt or check that `GEMINI_API_KEY` is valid.

**`UnsafeCommandError: Unsafe command detected`**
The Gemini-generated pillar command contained a destructive pattern. This is a safety guard. Check the ticket description — if Gemini is confused, refine `service_hint` on the ticket.

**`RuntimeError: No cached run result for ticket ...`**
`complete_ticket()` was called before `run_ticket()`. Always call `run_ticket()` first to populate the cache.

**`filelock.Timeout`**
Two processes tried to write to `knowledge_base.jsonl` simultaneously. The file lock has a default timeout; retry or increase the timeout in `KBStore`.

**ElevenLabs returns empty bytes**
Check `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`. The voice ID must match a voice available in your ElevenLabs account. The default `Rachel` voice is available on all plans.

**Poller logs `Failed to list open tickets`**
The `ERPClient.list_open_tickets()` raised an exception. Check `ERP_BASE_URL` and `ERP_BEARER_TOKEN` in your `.env`.
