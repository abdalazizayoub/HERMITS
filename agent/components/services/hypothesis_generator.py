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
You are a senior Linux sysadmin. Analyse the ticket, recon data, pillar baseline results, and past incidents. Generate EXACTLY 3 distinct hypotheses ranked from most to least likely. Each must have a different root cause. Then select the single best hypothesis you are most confident in and set best_hypothesis_index to the index of that chosen hypothesis. Do not randomly choose a hypothesis; choose it based on evidence and confidence. Return ONLY valid JSON matching this schema exactly, no markdown:

{{
  "hypotheses": [
    {{
      "hypothesis_title": "...",
      "root_cause_explanation": "...",
      "evidence": ["log line or recon signal"],
      "fix_steps": [
        {{"command": "...", "rationale": "...", "risk_level": "low|medium|high"}}
      ],
      "expected_pillar_outcomes": {{
        "service_state": "...",
        "functional_impact": "...",
        "durability": "..."
      }},
      "confidence_rationale": "..."
    }}
  ],
  "best_hypothesis_index": 0,
  "selection_rationale": "This hypothesis is most supported by the recon evidence because..."
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
            f"</recon>\n\n"
            f"<pillar_baseline>\n"
            f"service_state: → {pillar_baseline.service_state_output}\n"
            f"functional_impact: → {pillar_baseline.functional_impact_output}\n"
            f"durability: → {pillar_baseline.durability_output}\n"
            f"</pillar_baseline>\n\n"
            f"<past_incidents>\n{past_incidents}\n</past_incidents>"
        )

    def generate(
        self,
        ticket: Ticket,
        recon_output: dict,
        pillar_baseline: PillarResult,
        kb_matches: list[KBMatch],
        memory_context: str,
    ) -> BestHypothesisResult:
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(memory_context=memory_context)
        user_message = self._build_user_message(ticket, recon_output, pillar_baseline, kb_matches)

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
