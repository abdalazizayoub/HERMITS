import logging

from components.gemini_client import GeminiClient
from components.models.pillar import PillarResult, ThreePillarSpec, ValidationResult
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.agent.pillar_validator")

_SYSTEM_PROMPT_TEMPLATE = """\
<policy>
{memory_context}
</policy>
You are a senior Linux sysadmin. You will assess whether three validation pillars have passed after a fix was applied. Compare the BEFORE and AFTER outputs for each pillar command and determine if the situation is now resolved. Return ONLY valid JSON, no markdown.

JSON schema:
{{
  "service_state_passed": true,
  "functional_impact_passed": true,
  "durability_passed": false,
  "overall_passed": false,
  "notes": "..."
}}"""


class PillarValidator:
    def __init__(self, client: GeminiClient | None = None):
        self.client = client or GeminiClient()

    def validate(
        self,
        pillar_spec: ThreePillarSpec,
        baseline: PillarResult,
        after: PillarResult,
        ticket: Ticket,
        memory_context: str = "",
    ) -> ValidationResult:
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(memory_context=memory_context)

        user_message = (
            f"Ticket description: {ticket.description}\n\n"
            f"Definition of done: {pillar_spec.definition_of_done}\n\n"
            f"--- Pillar 1: service_state ---\n"
            f"Command: {pillar_spec.service_state_cmd}\n"
            f"BEFORE: {baseline.service_state_output}\n"
            f"AFTER:  {after.service_state_output}\n\n"
            f"--- Pillar 2: functional_impact ---\n"
            f"Command: {pillar_spec.functional_impact_cmd}\n"
            f"BEFORE: {baseline.functional_impact_output}\n"
            f"AFTER:  {after.functional_impact_output}\n\n"
            f"--- Pillar 3: durability ---\n"
            f"Command: {pillar_spec.durability_cmd}\n"
            f"BEFORE: {baseline.durability_output}\n"
            f"AFTER:  {after.durability_output}"
        )

        data = self.client.generate_json(system_prompt, user_message)
        result = ValidationResult(**data)
        logger.info(
            "Validation for ticket %s: overall_passed=%s",
            ticket.id,
            result.overall_passed,
        )
        return result
