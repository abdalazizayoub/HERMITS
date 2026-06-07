#!/usr/bin/env python3
"""
HERMITS CLI — end-to-end incident response pipeline with interactive command approval.

Run against a live HERMITS server (default: http://localhost:8080).

Usage:
    python hermits_cli.py <ticket_id>
    python hermits_cli.py <ticket_id> --server http://localhost:8000
    python hermits_cli.py <ticket_id> --technician alice
    python hermits_cli.py <ticket_id> --dry-run   # skip SSH execution, just show plan
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    sys.exit("httpx is required: pip install httpx")

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"

def _c(colour: str, text: str) -> str:
    return f"{colour}{text}{RESET}"

def _banner(title: str) -> None:
    bar = "─" * 60
    print(f"\n{_c(CYAN, bar)}")
    print(f"{_c(BOLD, f'  {title}')}")
    print(_c(CYAN, bar))

def _ok(msg: str)   -> None: print(f"  {_c(GREEN,  '✓')} {msg}")
def _err(msg: str)  -> None: print(f"  {_c(RED,    '✗')} {msg}")
def _info(msg: str) -> None: print(f"  {_c(CYAN,   '·')} {msg}")
def _warn(msg: str) -> None: print(f"  {_c(YELLOW, '!')} {msg}")

RISK_COLOUR = {"low": GREEN, "medium": YELLOW, "high": RED}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def post(client: httpx.Client, url: str, payload: dict,
         timeout: float = 90.0, fatal: bool = True) -> dict | None:
    try:
        r = client.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        _err(f"HTTP {e.response.status_code} from {url}")
        try:
            detail = e.response.json().get("detail", e.response.text[:300])
        except Exception:
            detail = e.response.text[:300]
        _err(f"  {detail}")
        if fatal:
            sys.exit(1)
        return None
    except httpx.RequestError as e:
        _err(f"Cannot reach server: {e}")
        if fatal:
            sys.exit(1)
        return None


# ── Interactive approve / decline ─────────────────────────────────────────────

def _prompt_command(idx: int, total: int, step: dict, dry_run: bool) -> bool:
    """Print the proposed command and ask the user to approve or decline."""
    cmd      = step.get("command", "")
    rationale = step.get("rationale", "—")
    risk      = step.get("risk_level", "unknown").lower()
    colour    = RISK_COLOUR.get(risk, WHITE)

    print()
    print(f"  {_c(BOLD, f'Command {idx}/{total}')}  {_c(colour, f'[{risk.upper()}]')}")
    print(f"  {_c(BOLD, 'CMD:')}  {_c(WHITE, cmd)}")
    print(f"  {_c(DIM,  'WHY:')}  {rationale}")

    if dry_run:
        _info("(dry-run — not executing)")
        return False

    while True:
        try:
            choice = input(f"\n  {_c(YELLOW, '[a]pprove / [d]ecline / [q]uit')} › ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            _warn("Interrupted — aborting")
            sys.exit(0)

        if choice in ("a", "approve", "y", "yes", ""):
            return True
        if choice in ("d", "decline", "n", "no", "skip"):
            return False
        if choice in ("q", "quit", "abort", "exit"):
            _warn("Aborted by user")
            sys.exit(0)
        _warn("Type  a  to approve,  d  to decline,  q  to quit")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(ticket_id: int, server: str, technician: str, dry_run: bool) -> None:
    base   = server.rstrip("/")
    client = httpx.Client(headers={"Content-Type": "application/json"})
    start  = time.time()

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    _banner(f"PHASE 1 — Open ticket {ticket_id}")
    _info("Generating pillar spec and capturing baseline over SSH (pillar commands run in parallel, ~30 s) …")
    phase1 = post(client, f"{base}/api/agent/ai/phase1",
                  {"ticket_id": ticket_id, "technician_id": technician},
                  timeout=300.0)

    spec = phase1.get("pillar_spec") or {}
    _ok(f"Pillar spec generated")
    _info(f"  service_state:      {spec.get('service_state_cmd', '—')}")
    _info(f"  functional_impact:  {spec.get('functional_impact_cmd', '—')}")
    _info(f"  durability:         {spec.get('durability_cmd', '—')}")
    _info(f"  definition_of_done: {spec.get('definition_of_done', '—')}")

    kb = phase1.get("kb_matches_initial", [])
    if kb:
        _ok(f"{len(kb)} KB match(es) found")
        for m in kb[:2]:
            entry = m.get("entry", {})
            _info(f"  [{m.get('similarity_score', 0):.2f}] {entry.get('root_cause', '')[:80]}")
    else:
        _info("No KB matches yet")

    # ── Recon ─────────────────────────────────────────────────────────────────
    _banner("RECON — SSH reconnaissance")
    _info("Running read-only commands on the VM (may take 30-90 s) …")
    recon_resp = post(client, f"{base}/api/agent/recon",
                      {"ticket_id": ticket_id},
                      timeout=300.0, fatal=False)

    if recon_resp is None:
        _warn("Recon failed — proceeding with empty recon (hypotheses may be less specific)")
        adapted, raw = {}, {}
    else:
        adapted = recon_resp.get("recon_adapted", {})
        raw     = recon_resp.get("recon", {})
        ssh_ok  = recon_resp.get("ssh_ok", True)
        if not ssh_ok:
            _warn(f"SSH recon partially failed: {raw.get('error', '')[:120]}")
            _info("Proceeding with partial recon data …")
        else:
            _ok("Recon complete")
        for key in ("logs", "service_statuses", "config_files", "port_config",
                    "service_users", "upload_dirs", "network", "database", "collector"):
            val = adapted.get(key, "")
            if val and val != "none found" and str(val).strip():
                snippet = str(val).replace("\n", " ")[:100]
                _info(f"  {key}: {snippet}")

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    _banner("PHASE 2 — Hypothesis generation")
    _info("Analysing recon data and generating fix hypotheses …")
    phase2 = post(client, f"{base}/api/agent/ai/phase2",
                  {"ticket_id": ticket_id, "technician_id": technician},
                  timeout=120.0, fatal=False)

    if phase2 is None:
        _warn("Phase 2 failed, retrying in 15 s …")
        time.sleep(15)
        phase2 = post(client, f"{base}/api/agent/ai/phase2",
                      {"ticket_id": ticket_id, "technician_id": technician},
                      timeout=120.0, fatal=True)

    best = phase2.get("best_hypothesis", {})
    hyp  = best.get("hypothesis", {})
    _ok(f"Best hypothesis: {_c(BOLD, hyp.get('hypothesis_title', '?'))}")
    _info(f"Root cause: {hyp.get('root_cause_explanation', '—')}")
    _info(f"Rationale:  {best.get('selection_rationale', '—')[:120]}")

    evidence = hyp.get("evidence", [])
    if evidence:
        _info("Evidence:")
        for e in evidence[:4]:
            _info(f"    • {str(e)[:100]}")

    fix_steps = hyp.get("fix_steps", [])
    if not fix_steps:
        _err("No fix steps generated — cannot continue")
        sys.exit(1)

    _info(f"{len(fix_steps)} fix step(s) proposed")

    # ── Repair loop: execute → validate → retry up to MAX_REPAIR times ───────
    MAX_REPAIR     = 2
    executed_steps: list[dict] = []
    command_decisions: list[list] = []
    passed     = False
    val_output = ""

    def _build_failure_context(executed: list[dict], validation_out: str) -> str:
        lines = ["Validation script output:", validation_out[:800], "",
                 "Commands already executed in previous attempt(s) — do NOT repeat these:"]
        for i, s in enumerate(executed, 1):
            ec = s.get("exit_code")
            lines.append(f"  [{i}] cmd: {s.get('command','')}")
            lines.append(f"       exit={ec}")
            if s.get("stdout"): lines.append(f"       stdout: {s['stdout'][:200]}")
            if s.get("stderr"): lines.append(f"       stderr: {s['stderr'][:150]}")
        lines.append("")
        lines.append("Generate a NEW plan that addresses what the previous attempt missed or got wrong.")
        return "\n".join(lines)

    for attempt in range(MAX_REPAIR + 1):
        if attempt > 0:
            _banner(f"REPAIR {attempt}/{MAX_REPAIR} — Re-generating hypothesis")
            _info("Validation failed. Asking the agent for a new fix plan …")
            phase2 = post(client, f"{base}/api/agent/ai/phase2", {
                "ticket_id":      ticket_id,
                "technician_id":  technician,
                "failure_context": _build_failure_context(executed_steps, val_output),
            }, timeout=120.0)
            best      = phase2.get("best_hypothesis", {})
            hyp       = best.get("hypothesis", {})
            fix_steps = hyp.get("fix_steps", [])
            if not fix_steps:
                _warn("No new fix steps — giving up")
                break
            _ok(f"New hypothesis: {_c(BOLD, hyp.get('hypothesis_title', '?'))}")
            _info(f"Root cause: {hyp.get('root_cause_explanation', '—')}")
            _info(f"{len(fix_steps)} new fix step(s) proposed")

        label = f"EXECUTE  (repair {attempt}/{MAX_REPAIR})" if attempt > 0 else "EXECUTE — Approve each command"
        _banner(label)
        print(f"  {_c(DIM, 'a=approve  d=decline  q=quit')}")

        for i, step in enumerate(fix_steps, 1):
            approved = _prompt_command(i, len(fix_steps), step, dry_run)
            command_decisions.append([step.get("command", ""), approved])

            if approved and not dry_run:
                result = post(client, f"{base}/api/agent/execute", {
                    "ticket_id": ticket_id,
                    "command":   step.get("command", ""),
                    "category":  step.get("risk_level", "fix"),
                }, timeout=180.0)

                blocked   = result.get("blocked", False)
                exit_code = result.get("exit_code")
                stdout    = (result.get("stdout") or "").strip()
                stderr    = (result.get("stderr") or "").strip()

                if blocked:
                    _err(f"BLOCKED by safety layer: {result.get('reason', '')}")
                    for w in result.get("warnings", []):
                        _warn(f"  {w}")
                elif exit_code is None:
                    _warn("exit=None (SSH timeout or connection failure)")
                    if stderr: _warn(f"  stderr: {stderr[:200]}")
                elif exit_code == 0:
                    _ok("exit=0")
                    if stdout:
                        _info(f"  stdout: {stdout[:200]}")
                else:
                    _warn(f"exit={exit_code}")
                    if stdout: _info(f"  stdout: {stdout[:200]}")
                    if stderr: _warn(f"  stderr: {stderr[:200]}")

                executed_steps.append({
                    "command":   step.get("command", ""),
                    "stdout":    stdout[:300],
                    "stderr":    stderr[:200],
                    "exit_code": exit_code,
                })
            elif not approved:
                _info("Skipped")

        # Validate after each attempt
        _banner("VALIDATE — public-test.sh")
        if dry_run:
            _info("(dry-run — skipping validation)")
            passed = False
            val_output = ""
            break

        _info("Running validation script on VM …")
        val_resp   = post(client, f"{base}/api/agent/validate",
                          {"ticket_id": ticket_id}, timeout=360.0)
        passed     = val_resp.get("passed", False)
        val_output = val_resp.get("output", "")

        if passed:
            _ok("Validation PASSED")
            break
        else:
            _err("Validation FAILED")
        for line in val_output.splitlines()[:20]:
            _info(f"  {line}")

        if attempt < MAX_REPAIR:
            try:
                retry = input(
                    f"\n  {_c(YELLOW, f'Try a new fix? [{attempt+1}/{MAX_REPAIR} retries left]  [y/N]')} › "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                retry = "n"
            if retry not in ("y", "yes"):
                break

    # ── Collect pillar-after results ───────────────────────────────────────────
    # Use the before-baseline as a template; the ERP drafter will use executed_steps
    # and validation output to determine actual outcome.
    pillar_baseline = phase1.get("pillar_baseline", {})
    pillar_after = {
        "service_state_output":    val_output[:500] if val_output else pillar_baseline.get("service_state_output", ""),
        "functional_impact_output": val_output[:500] if val_output else pillar_baseline.get("functional_impact_output", ""),
        "durability_output":        val_output[:500] if val_output else pillar_baseline.get("durability_output", ""),
    }

    # ── Complete ──────────────────────────────────────────────────────────────
    _banner("COMPLETE — Draft ERP activity")
    elapsed_min = max(1, int((time.time() - start) / 60))

    notes = ""
    try:
        notes = input(f"\n  {_c(YELLOW, 'Technician notes (optional, Enter to skip)')} › ").strip()
    except (EOFError, KeyboardInterrupt):
        pass

    complete = post(client, f"{base}/api/agent/ai/complete", {
        "ticket_id":               ticket_id,
        "chosen_hypothesis_index": 0,
        "pillar_after_results":    pillar_after,
        "executed_steps":          executed_steps,
        "technician_id":           technician,
        "technician_notes":        notes,
        "resolution_time_minutes": elapsed_min,
        "command_decisions":       command_decisions,
    }, timeout=120.0)

    activity = complete.get("activity", {})
    _ok("Activity drafted")
    _info(f"  summary:     {activity.get('summary', '')[:120]}")
    _info(f"  root_cause:  {activity.get('root_cause', '')[:120]}")
    _info(f"  validation:  {activity.get('validation_result', '')[:120]}")

    # ── Submit ────────────────────────────────────────────────────────────────
    _banner("SUBMIT — Post to Phoenix ERP")

    if dry_run:
        _info("(dry-run — not submitting to ERP)")
    else:
        try:
            confirm = input(f"\n  {_c(YELLOW, 'Submit activity to ERP? [y/N]')} › ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"

        if confirm in ("y", "yes"):
            post(client, f"{base}/api/activities/submit", {
                "ticket_id":         ticket_id,
                "start_datetime":    activity.get("start_datetime", datetime.now(timezone.utc).isoformat()),
                "end_datetime":      activity.get("end_datetime",   datetime.now(timezone.utc).isoformat()),
                "summary":           activity.get("summary", ""),
                "root_cause":        activity.get("root_cause", ""),
                "actions_taken":     activity.get("actions_taken", ""),
                "commands_summary":  activity.get("commands_summary", ""),
                "validation_result": activity.get("validation_result", ""),
            }, timeout=30.0)
            _ok("Activity submitted — ticket marked DONE")
        else:
            _info("Skipped ERP submission")

    # ── Summary ───────────────────────────────────────────────────────────────
    _banner("DONE")
    status = _c(GREEN, "PASSED") if passed else _c(RED, "FAILED")
    print(f"  Ticket:     {ticket_id}")
    print(f"  Validation: {status}")
    print(f"  Duration:   {elapsed_min} min")
    print(f"  Commands:   {len([d for d in command_decisions if d[1]])} approved / "
          f"{len([d for d in command_decisions if not d[1]])} declined")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="HERMITS CLI — interactive incident response pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("ticket_id", type=int, help="Phoenix ERP ticket ID")
    p.add_argument("--server",     default="http://localhost:8080",
                   help="HERMITS server base URL (default: http://localhost:8080)")
    p.add_argument("--technician", default="cli-user",
                   help="Technician ID recorded in audit log (default: cli-user)")
    p.add_argument("--dry-run", action="store_true",
                   help="Show proposed fix steps without executing or submitting")
    args = p.parse_args()

    print(_c(BOLD, "\n  HERMITS — Incident Response CLI"))
    print(_c(DIM,  f"  server={args.server}  ticket={args.ticket_id}  tech={args.technician}"))
    if args.dry_run:
        print(_c(YELLOW, "  DRY-RUN MODE — commands will not be executed"))

    run(args.ticket_id, args.server, args.technician, args.dry_run)


if __name__ == "__main__":
    main()
