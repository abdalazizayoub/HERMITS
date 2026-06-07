import logging
import re

from components.gemini_client import GeminiClient, GeminiParseError
from components.models.pillar import ThreePillarSpec
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.agent.three_pillars")

_UNSAFE_PATTERNS = re.compile(
    r"\b(rm|dd|mkfs|chmod|chown)\b"
    r"|systemctl\s+(stop|disable|restart|start)\b"
    r"|\b(kill|pkill|shutdown|reboot|halt)\b"
    r"|>\s*/dev/(?!null\b)"
    r"|\bDROP\s+(TABLE|DATABASE)\b"
    r"|public-test\.sh",
    re.IGNORECASE,
)

_SYSTEM_PROMPT_TEMPLATE = """\
<policy>
{memory_context}
</policy>
You are a senior Linux sysadmin. Given a ticket, generate exactly 3 lightweight read-only bash commands that measure whether the incident is resolved. These commands run as a BASELINE before any fix — they must be safe to run at any time without affecting service state.

HARD CONSTRAINTS (violated commands will be rejected):
- No sudo — all commands must run as the SSH user without privilege escalation
- No service restarts or starts — no systemctl restart/start/stop/enable/disable
- No /opt/hackathon/public-test.sh — that is only for final validation, not baseline measurement
- No file writes, no reboots, no kills
- Each command must complete in under 10 seconds

Good baseline commands: curl -s -o /dev/null -w "%{{http_code}}", systemctl is-active, systemctl is-enabled, ss -tlnp | grep <port>, getent hosts <hostname>, psql -c "SELECT ...", journalctl -n 5 --no-pager

Return ONLY valid JSON, no markdown, no explanation.

The JSON must match this schema exactly:
{{
  "service_state_cmd": "...",
  "functional_impact_cmd": "...",
  "durability_cmd": "...",
  "definition_of_done": "..."
}}"""


class UnsafeCommandError(Exception):
    pass


class ThreePillarGenerationError(Exception):
    pass


class ThreePillarsGenerator:
    def __init__(self, client: GeminiClient | None = None):
        self.client = client or GeminiClient()

    def _check_safety(self, spec: ThreePillarSpec) -> None:
        for cmd in (spec.service_state_cmd, spec.functional_impact_cmd, spec.durability_cmd):
            if _UNSAFE_PATTERNS.search(cmd):
                raise UnsafeCommandError(f"Unsafe command detected: {cmd[:80]}")

    def generate(self, ticket: Ticket, memory_context: str = "") -> ThreePillarSpec:
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(memory_context=memory_context)
        title = ticket.title.strip().replace("\n", " ")[:200]
        description = ticket.description.strip().replace("\n", " ")[:600]
        service_hint = ticket.service_hint or "unknown"
        user_message = (
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Service hint: {service_hint}"
        )

        last_error = None
        for attempt in range(2):
            try:
                data = self.client.generate_json(system_prompt, user_message, max_retries=1)
                spec = ThreePillarSpec(**data)
                self._check_safety(spec)
                return spec
            except (GeminiParseError, KeyError, TypeError, ValueError) as e:
                last_error = e
                logger.warning("ThreePillars attempt %d failed: %s", attempt + 1, e)
            except UnsafeCommandError:
                raise

        raise ThreePillarGenerationError(
            f"Failed to generate valid three pillars after 2 attempts: {last_error}"
        )
