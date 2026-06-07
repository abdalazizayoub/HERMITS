import json
import logging
from datetime import datetime

from components.gemini_client import GeminiClient, GeminiParseError
from components.models.hypothesis import BestHypothesisResult, Hypothesis
from components.models.kb_entry import KBMatch
from components.models.pillar import PillarResult
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.agent.hypothesis_generator")

_SYSTEM_PROMPT_TEMPLATE = """\
<policy>
{memory_context}
</policy>

You are a senior Linux SRE diagnosing a production incident on an Ubuntu VM. Your job is to produce fix steps that work on the first attempt. Sloppy diagnosis wastes time; incomplete fixes score zero.

Read the recon data provided. Extract specific values. Then build hypotheses from evidence, not from assumptions.

---

## STEP 1 — EXTRACT SIGNALS FROM RECON (do this before forming any hypothesis)

Scan each recon section and note concrete values:

`pillar_baseline` — what exact error does the baseline show?
  - Connection refused on port X → port mismatch or service down
  - "role does not exist" → missing PostgreSQL role
  - Permission denied / EACCES → ownership mismatch
  - Name or service not known / EAI_NONAME → DNS resolution failure

`config_files` — look for PORT=, BIND=, LISTEN=, HOST=, URL= values that conflict with the ticket's expected endpoint

`service_statuses` — any unit in failed / inactive / disabled?

`service_users` — what User= does the relevant service declare?

`upload_dirs` — what user:group owns the directory? Does it match service_users?

`network` — is the hostname from the ticket present in /etc/hosts? Does it resolve to the right IP?

`database` — three things to check:
  (a) pg_users: which role is the application user? (exclude postgres and pg_* system roles)
  (b) pg_grants: does that role have INSERT and UPDATE on the relevant tables?
  (c) pg_seq_grants: does that role have USAGE on sequences? (NULL relacl = no grants)

`collector_detail` — any monitoring/agent/metric service in inactive or failed state?

---

## STEP 2 — MATCH SIGNALS TO PATTERNS

⚠ MULTI-ISSUE RULE: Many incidents have two concurrent root causes. Your winning hypothesis must fix ALL of them. A port fix without an enable is incomplete. A table GRANT without a sequence GRANT will still fail on INSERT.

**PORT MISMATCH**
Signal: config_files shows PORT=Y, but the ticket URL or pillar_baseline curl targets port X (X ≠ Y).
Fix:
  sudo sed -i 's/PORT=Y/PORT=X/' /exact/env/file
  sudo systemctl daemon-reload
  sudo systemctl enable <service>
  sudo systemctl restart --no-block <service>

**SERVICE NOT ENABLED**
Signal: service_statuses shows a unit that is loaded but not enabled, or systemctl is-enabled returns "disabled".
Always cross-check for a port mismatch too — both often co-occur.
Fix: sudo systemctl enable <service> && sudo systemctl restart --no-block <service>

**FILESYSTEM PERMISSION**
Signal: upload_dirs shows root:root (or wrong owner) but service_users shows a different User=.
Use the exact User= value from service_users. Use the exact directory from upload_dirs.
Fix: sudo chown -R <user>:<user> <exact_path>
Never use chmod. Never guess the path.

**DNS MISSING**
Signal: hostname from the ticket description is absent from /etc/hosts, or pillar_baseline shows EAI_NONAME.
If the service is local (a process is listening on that port per port_config), map it to 127.0.0.1.
Fix: echo "127.0.0.1 <hostname>" | sudo tee -a /etc/hosts

**DATABASE WRITE BLOCKED**
Signal: application can read but not write, or pg_grants shows no INSERT/UPDATE for the app role.
Critical: INSERT on any table with a SERIAL or BIGSERIAL primary key calls nextval() on a sequence.
That requires a separate USAGE grant on sequences. If you only grant table privileges, INSERT still fails.
Fix — both steps are required:
  sudo -u postgres psql -c "GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO <app_role>;"
  sudo -u postgres psql -c "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO <app_role>;"
Identify <app_role> from pg_users: it is the non-system role the application uses, not 'postgres'.

**COLLECTOR NOT RUNNING**
Signal: collector_detail shows a metric/agent/log service in inactive or failed state.
Fix: sudo systemctl enable --now <service_name>

---

## STEP 3 — WRITE FIX STEPS

Rules (a partial fix scores zero):
1. Quote exact values from recon — if a path, username, port, or role is not in the recon, add a read-only diagnostic command first before the fix
2. Service fixes must follow this exact order: daemon-reload → enable → restart --no-block
3. Database fixes must include BOTH table grant AND sequence grant
4. The final step in fix_steps must always be:
   {{"command": "sudo /opt/hackathon/public-test.sh", "rationale": "Validates the fix with the official grader", "risk_level": "low"}}
5. Every state-modifying command requires sudo

Missing evidence → add a diagnostic read step first:
- Unknown upload path: {{"command": "find /opt /srv /var/www -name '*.py' 2>/dev/null | xargs grep -in 'upload\\\\|path\\\\|folder\\\\|dir' 2>/dev/null | head -20", "rationale": "Find exact upload path from source", "risk_level": "low"}}
- Unknown service name: {{"command": "systemctl list-units --type=service --state=active --no-pager | head -30", "rationale": "Find the running service name", "risk_level": "low"}}
- Unknown port config: {{"command": "find /etc /opt -name '*.env' -o -name '*.conf' 2>/dev/null | xargs grep -i 'port\\\\|bind\\\\|listen' 2>/dev/null | head -20", "rationale": "Find port config location", "risk_level": "low"}}

---

## STEP 4 — SAFETY

Never propose: rm -rf, chmod -R 777, DROP TABLE, DROP DATABASE, ufw disable, deleting logs, changing passwords.

---

Return exactly this JSON (no markdown, no explanation).
IMPORTANT: the "hypotheses" array MUST contain EXACTLY 3 objects — no more, no fewer.
Index 0 = most confident, index 1 = second, index 2 = third (or a fallback/novel hypothesis).
{{
  "hypotheses": [
    {{
      "hypothesis_title": "concise root cause label for hypothesis 0 (most confident)",
      "root_cause_explanation": "specific technical cause — name the exact file, value, missing grant, or wrong owner; not the user-facing symptom",
      "evidence": ["direct quote or value from the recon that proves this — not a paraphrase"],
      "fix_steps": [
        {{"command": "exact command with real values substituted from recon", "rationale": "why this step is necessary", "risk_level": "low|medium|high"}}
      ],
      "expected_pillar_outcomes": {{
        "service_state": "expected output after fix",
        "functional_impact": "PASS",
        "durability": "persists after reboot"
      }},
      "confidence_rationale": "why this ranks 1st relative to the other hypotheses"
    }},
    {{
      "hypothesis_title": "concise root cause label for hypothesis 1 (second most confident)",
      "root_cause_explanation": "specific technical cause — name the exact file, value, missing grant, or wrong owner; not the user-facing symptom",
      "evidence": ["direct quote or value from the recon that supports this"],
      "fix_steps": [
        {{"command": "exact command with real values substituted from recon", "rationale": "why this step is necessary", "risk_level": "low|medium|high"}}
      ],
      "expected_pillar_outcomes": {{
        "service_state": "expected output after fix",
        "functional_impact": "PASS",
        "durability": "persists after reboot"
      }},
      "confidence_rationale": "why this ranks 2nd relative to the other hypotheses"
    }},
    {{
      "hypothesis_title": "concise root cause label for hypothesis 2 (third / fallback)",
      "root_cause_explanation": "specific technical cause — name the exact file, value, missing grant, or wrong owner; not the user-facing symptom",
      "evidence": ["direct quote or value from the recon that supports this"],
      "fix_steps": [
        {{"command": "exact command with real values substituted from recon", "rationale": "why this step is necessary", "risk_level": "low|medium|high"}}
      ],
      "expected_pillar_outcomes": {{
        "service_state": "expected output after fix",
        "functional_impact": "PASS",
        "durability": "persists after reboot"
      }},
      "confidence_rationale": "why this ranks 3rd relative to the other hypotheses"
    }}
  ],
  "best_hypothesis_index": 0,
  "selection_rationale": "which recon signals most directly support this hypothesis over the alternatives"
}}"""


class HypothesisGenerationError(Exception):
    pass


class HypothesisGenerator:
    def __init__(self, client: GeminiClient | None = None):
        self.client = client or GeminiClient()

    def _build_user_message(
        self,
        ticket: Ticket,
        recon_output: dict,
        pillar_baseline: PillarResult,
        kb_matches: list[KBMatch],
        failure_context: str = "",
    ) -> str:
        logs = recon_output.get("logs", [])
        if isinstance(logs, list):
            log_lines = logs[-100:]
        else:
            log_lines = str(logs).splitlines()[-100:]

        past_incidents = json.dumps(
            [m.entry.model_dump() for m in kb_matches[:3]],
            default=str,
            indent=2,
        )

        return (
            f"<ticket>\n"
            f"title: {ticket.title}\n"
            f"description: {ticket.description}\n"
            f"service_hint: {ticket.service_hint or 'unknown'}\n"
            f"priority: {ticket.priority}\n"
            f"</ticket>\n\n"
            f"<recon>\n"
            f"logs: {log_lines}\n"
            f"service_statuses: {recon_output.get('service_statuses', {})}\n"
            f"disk_usage: {recon_output.get('disk_usage', {})}\n"
            f"processes: {recon_output.get('processes', [])[:20]}\n"
            f"cron_timers: {recon_output.get('cron_timers', [])}\n"
            f"config_files: {recon_output.get('config_files', 'none found')}\n"
            f"port_config: {recon_output.get('port_config', 'none found')}\n"
            f"service_users: {recon_output.get('service_users', 'none found')}\n"
            f"upload_dirs: {recon_output.get('upload_dirs', 'none found')}\n"
            f"app_source: {str(recon_output.get('app_source', ''))[:3000] or 'none found'}\n"
            f"network: {recon_output.get('network', 'none found')}\n"
            f"database: {recon_output.get('database', 'none found')}\n"
            f"collector: {recon_output.get('collector', 'none found')}\n"
            f"collector_detail: {recon_output.get('collector_detail', 'none found')}\n"
            f"</recon>\n\n"
            f"<pillar_baseline>\n"
            f"service_state: → {pillar_baseline.service_state_output}\n"
            f"functional_impact: → {pillar_baseline.functional_impact_output}\n"
            f"durability: → {pillar_baseline.durability_output}\n"
            f"</pillar_baseline>\n\n"
            f"<past_incidents>\n{past_incidents}\n</past_incidents>"
            + (
                f"\n\n<previous_fix_attempt_failed>\n"
                f"A previous fix was applied but the system is STILL BROKEN.\n"
                f"Validation output showing what remains failing:\n{failure_context[:1000]}\n"
                f"Generate NEW hypotheses targeting what the previous fix missed. "
                f"Do NOT repeat commands that were already tried.\n"
                f"</previous_fix_attempt_failed>"
                if failure_context else ""
            )
        )

    def generate(
        self,
        ticket: Ticket,
        recon_output: dict,
        pillar_baseline: PillarResult,
        kb_matches: list[KBMatch],
        memory_context: str,
        failure_context: str = "",
    ) -> BestHypothesisResult:
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(memory_context=memory_context)
        user_message = self._build_user_message(
            ticket, recon_output, pillar_baseline, kb_matches, failure_context
        )

        last_error = None
        for attempt in range(2):
            try:
                data = self.client.generate_json(system_prompt, user_message, max_retries=1)
                hypotheses_data = data.get("hypotheses", [])
                if len(hypotheses_data) != 3:
                    raise ValueError(
                        f"Expected exactly 3 hypotheses, got {len(hypotheses_data)}"
                    )
                best_index = data.get("best_hypothesis_index")
                if best_index not in (0, 1, 2):
                    raise ValueError(
                        f"best_hypothesis_index must be 0, 1, or 2, got {best_index!r}"
                    )
                selection_rationale = data.get("selection_rationale", "")
                hypotheses = [Hypothesis(**h) for h in hypotheses_data]
                return BestHypothesisResult(
                    hypothesis=hypotheses[best_index],
                    selection_rationale=selection_rationale,
                    ticket_id=ticket.id,
                    generated_at=datetime.utcnow(),
                )
            except (GeminiParseError, KeyError, TypeError, ValueError) as e:
                last_error = e
                logger.warning("HypothesisGenerator attempt %d failed: %s", attempt + 1, e)

        raise HypothesisGenerationError(
            f"Failed to generate best hypothesis after 2 attempts: {last_error}"
        )
