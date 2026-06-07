# HERMITS: Technical Report & Architecture Overview
### Hybrid Engine for Remediation, Monitoring & IT Support
**START Hack Vienna 2026 — techbold Track Submission**

---

## 1. Executive Summary
HERMITS is an intelligent, human-in-the-loop AI Service Desk Autopilot designed to solve the challenges of modern Managed IT Service Providers (MSPs). Traditional automation breaks when confronted with non-deterministic system environments, while unconstrained AI agents pose severe operational risks by executing destructive commands or failing to recognize co-occurring infrastructure faults. 

HERMITS bridges this gap by acting as a senior Linux SRE that programmatically discovers system state, matches anomalies against structured engineering patterns, constructs ranked fix proposals, and executes approved steps under strict technician control. By enforcing multi-pillar baseline tracking, rigid sandboxing, and automated activity logging, HERMITS dramatically slashes Mean Time to Resolution (MTTR) while maintaining total operational safety.

---

## 2. System Architecture & Lifecycle Pipeline
The application decouples core AI orchestration from low-level infrastructure interaction, running entirely within a multi-container Docker environment.

[ Phoenix ERP ] ---> [ FastAPI Backend Router ] ---> [ Frontend Dashboard Viewport ]
|
v
[ Gemini 2.5 Flash / Pro Engine ]
|
(Secure SSH Tunnel)
|
v
[ Target Customer Linux VM ]

The troubleshooting engine executes a deterministic 5-phase loop for every incident:
1. **Phase 1: Three-Pillar Baseline Generation:** Triggered automatically upon ticket acquisition. The LLM constructs exactly three safe, lightweight, non-privileged verification vectors to quantify the outage state.
2. **Phase 2: 13-Point Parallel Deep Reconnaissance:** The backend executes a fast, batched suite of read-only terminal commands over SSH to map out disk health, systemd structures, network bindings, and database configurations.
3. **Phase 3: Root Cause Pattern Matching & Ranking:** The agent combines raw recon state, pillar errors, and historical knowledge base entries to synthesize three distinct technical hypotheses accompanied by sequential bash commands.
4. **Phase 4: Human-In-The-Loop Execution:** Every single state-modifying action must be manually validated and explicitly unblocked by the technician via the UI terminal console.
5. **Phase 5: Integrity Verification & ERP Commit:** The system executes the official grader script (`public-test.sh`). Upon achieving a true `PASS`, the engine auto-drafts a detailed markdown log detailing the exact terminal diffs and commits it to close the Phoenix ERP case file.

---

## 3. Core Technical Modules

### A. Asynchronous SSH Runner (`backend/servers/ssh/runner.py`)
Low-level networking utilizes the concurrent `asyncssh` library. To prevent self-inflicted Denial of Service (DoS) attacks on target OpenSSH daemons—which typically enforce a default maximum limit of 10 concurrent unauthenticated sessions (`MaxSessions`)—the runner implements strict batch scheduling. Primitives are dispatched concurrently in groups of 8 using `asyncio.gather`, dramatically decreasing system inventory lookup times without triggering SSH drops.

### B. Dual-Tier LLM & Reasoning Escalation (`agent/components/gemini_client.py`)
The system introduces an automated tier-shifting reasoning logic to maximize execution efficiency:
* **Tier 1 (Default):** `gemini-2.5-flash` executes initial high-speed structured JSON formatting, baseline generation, and standard text summaries.
* **Tier 3 (Escalation Fallback):** If an approved action sequence fails the final `public-test.sh` evaluation, the controller automatically catches the failure context and hot-swaps the underlying model engine to `gemini-2.5-pro`. This feeds up to 100 lines of complex target kernel/journalctl outputs into a higher-capacity reasoning model to troubleshoot nuanced edge cases.

### C. Pattern-Driven Hypothesis Formulation (`agent/components/services/hypothesis_generator.py`)
Instead of allowing open-ended shell generations, the engine constraints the AI using explicit SRE heuristics encoded into system prompt rules:
* **The Multi-Issue Resolution Rule:** Teaches the agent to catch overlapping faults (e.g., matching a configuration port shift with an un-enabled systemd service, or executing database table `GRANT` rules alongside mandatory relational sequence updates).
* **Forced Execution Sequence:** Mandates that configuration corrections occur entirely *before* service lifecycles change: `[File Mutation via Sed/Tee] -> daemon-reload -> systemctl enable -> systemctl restart --no-block`.

---

## 4. Multi-Layered Safety Infrastructure
Operating on live customer workloads requires safety constraints independent of model behavioral alignment. HERMITS deploys two rigid security perimeters:

### A. Pre-Execution Token Inspection (`backend/servers/ssh/safety.py`)
Incoming bash strings are fully disassembled before being forwarded to the remote PTY wrapper. The pipeline executes shell-tokenization via Python's built-in `shlex` pipeline, splitting commands across operators (`|`, `&&`, `||`). The system checks the base executable against a strict structural blocklist:
* **Hard Blocked Commands (Immediate Rejection):** `rm -rf /`, `chmod -R 777`, `ufw disable`, `DROP DATABASE`, `truncate /var/log`, `history -c`.
* **Warning Warnings (Logged flag indicators):** `reboot`, `halt`, `apt remove`.

### B. Multi-Pillar Constraint Guardrails
During the Phase 1 generation loop, the system prompt actively strips administrative rights by explicitly preventing the generation of `sudo` tokens or access to structural validator files (`public-test.sh`). The backend regex filters baseline commands to guarantee zero write operations occur during pure diagnostic checks.

---

## 5. Technology Stack & Ecosystem Primitives
* **Languages:** Python (Backend Orchestration), TypeScript (State-Machine UI Viewport), Bash (Target Shell Automation)
* **Frameworks:** FastAPI (Asynchronous Async REST Router Engine), React v18 (Single Page Dashboard Workspace)
* **Build Tooling & Infrastructure:** Vite (High-Speed Frontend Compilation), Docker & Docker Compose (Multi-Container Virtualized Sandbox Layout)
* **Libraries:** AsyncSSH (Concurrent Remote Terminal Pipelines), Pydantic (Declarative Data-Shape Validation & Schema Output Enforcement)
* **AI Orchestration:** Google GenAI SDK (`gemini-2.5-flash` & `gemini-2.5-pro`)

---

## 6. Engineering Assumptions & Operational Guardrails
1. **Privilege Demarcation:** It is assumed that the SSH user account configured for basic reconnaissance possesses standard read privileges across active log paths, with fallback paths configured via `sudo -n cat` for critical configuration trees like PostgreSQL's `pg_hba.conf`.
2. **Postgres Auth Topology:** Database discovery assumes that local operations allow standard unauthenticated socket connections or peer mapping for administrative configuration lookups via the `postgres` system user.
3. **Network Persistence:** Target virtual machines are assumed to maintain a reliable, continuous route layer. To mitigate brief network drops during hard service recycles, connection clients utilize an automatic three-tier retry loop configured with a 20-second step-back delay
