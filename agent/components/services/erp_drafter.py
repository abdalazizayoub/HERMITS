import logging
import re
from datetime import datetime, timezone
from typing import Optional

from components.gemini_client import GeminiClient
from components.models.activity import Activity
from components.models.hypothesis import Hypothesis
from components.models.pillar import ValidationResult
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.agent.erp_drafter")

_SYSTEM_PROMPT = """\
<policy>
{memory_context}
</policy>
You are a senior Linux sysadmin writing an ERP incident activity report. Produce ALL five required fields in JSON. Be precise and technical. IMPORTANT: the commands_summary field must NEVER contain output values, secrets, passwords, tokens, keys, credentials, or base64 strings longer than 20 characters. Scrub any string matching password, token, key, secret, private, credential, or long base64 from commands_summary before including it. Return ONLY valid JSON, no markdown.

root_cause must be the specific technical configuration error, not the symptom.
BAD: "The status API was not available"
GOOD: "PORT=8008 in /etc/customer-status.env caused the service to bind to the wrong port; the service was also not enabled for automatic startup"

JSON schema:
{{
  "summary": "one concise sentence of what happened and what was done",
  "root_cause": "the misconfigured file, value, or missing setting — not the user-facing symptom",
  "actions_taken": "numbered list of diagnosis steps then fix steps in chronological order",
  "commands_summary": "list of commands run — NO output, NO secrets, NO passwords, NO tokens, NO private keys",
  "validation_result": "concrete proof — quote pillar outputs showing PASS, state what was verified"
}}"""

_SECRET_RE = re.compile(
    r"(password|token|key|secret|private|credential)[^\s]*\s*[=:]\s*\S+",
    re.IGNORECASE,
)
_BASE64_RE = re.compile(r"[A-Za-z0-9+/]{21,}={0,2}")


def _scrub_secrets(text: str) -> str:
    text = _SECRET_RE.sub("[REDACTED]", text)
    text = _BASE64_RE.sub("[REDACTED]", text)
    return text


class ERPDrafter:
    def __init__(self, client: GeminiClient | None = None):
        self.client = client or GeminiClient()

    def draft(
        self,
        ticket: Ticket,
        chosen_hypothesis: Hypothesis,
        executed_steps: list[dict],
        validation_result: ValidationResult,
        technician_notes: str,
        memory_context: str = "",
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
    ) -> Activity:
        system_prompt = _SYSTEM_PROMPT.format(memory_context=memory_context)

        steps_text = "\n".join(
            f"  - [{s.get('timestamp', '')}] {s.get('command', '')} "
            f"(approved={s.get('approved', False)})"
            for s in executed_steps
        )

        user_message = (
            f"Ticket ID: {ticket.id}\n"
            f"Customer: {ticket.customer_name}\n"
            f"Title: {ticket.title}\n"
            f"Priority: {ticket.priority}\n\n"
            f"Chosen hypothesis: {chosen_hypothesis.hypothesis_title}\n"
            f"Root cause: {chosen_hypothesis.root_cause_explanation}\n\n"
            f"Executed steps:\n{steps_text}\n\n"
            f"Validation result:\n"
            f"  service_state_passed: {validation_result.service_state_passed}\n"
            f"  functional_impact_passed: {validation_result.functional_impact_passed}\n"
            f"  durability_passed: {validation_result.durability_passed}\n"
            f"  overall_passed: {validation_result.overall_passed}\n"
            f"  notes: {validation_result.notes}\n\n"
            f"Technician notes: {technician_notes}"
        )

        data = self.client.generate_json(system_prompt, user_message)

        # Gemini sometimes returns list-typed values when the schema says "list of …".
        # Coerce every field to str before doing anything else.
        for field in ("summary", "root_cause", "actions_taken",
                      "commands_summary", "validation_result"):
            val = data.get(field, "")
            if isinstance(val, list):
                data[field] = "\n".join(str(item) for item in val)
            elif not isinstance(val, str):
                data[field] = str(val) if val is not None else ""

        # Scrub secrets from commands_summary even if Gemini missed it
        data["commands_summary"] = _scrub_secrets(data.get("commands_summary", ""))

        def _ensure_utc(dt: Optional[datetime]) -> datetime:
            if dt is None:
                return datetime.now(timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        activity = Activity(
            ticket_id=ticket.id,
            start_datetime=_ensure_utc(start_datetime),
            end_datetime=_ensure_utc(end_datetime),
            summary=data["summary"],
            root_cause=data["root_cause"],
            actions_taken=data["actions_taken"],
            commands_summary=data["commands_summary"],
            validation_result=data["validation_result"],
        )
        logger.info("ERP activity drafted for ticket %s", ticket.id)
        return activity
