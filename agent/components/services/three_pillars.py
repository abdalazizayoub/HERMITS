import logging
import re

from components.gemini_client import GeminiClient, GeminiParseError
from components.models.pillar import ThreePillarSpec
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.agent.three_pillars")

_UNSAFE_PATTERNS = re.compile(
    r"\b(rm|dd|mkfs|chmod|chown)\b"
    r"|systemctl\s+(stop|disable)\b"
    r"|\b(kill|pkill|shutdown|reboot|halt)\b"
    r"|>\s*/dev/"
    r"|\bDROP\s+(TABLE|DATABASE)\b",
    re.IGNORECASE,
)

_SYSTEM_PROMPT_TEMPLATE = """\
<policy>
{memory_context}
</policy>
You are a senior Linux sysadmin. Given a ticket, generate exactly 3 read-only bash validation commands that define what "fixed" looks like. Return ONLY valid JSON, no markdown, no explanation.

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
        user_message = (
            f"Title: {ticket.title}\n"
            f"Description: {ticket.description}\n"
            f"Service hint: {ticket.service_hint or 'unknown'}"
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
