import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from components.services.erp_drafter import ERPDrafter
from components.services.hypothesis_generator import HypothesisGenerator
from components.services.pillar_validator import PillarValidator
from components.services.safety import SafetyCheckResult, SafetyLayer
from components.services.three_pillars import ThreePillarsGenerator
from components.services.trust_calibrator import TrustCalibrator
from components.knowledge_base.matcher import KBMatcher
from components.knowledge_base.writer import KBWriter
from components.memory.context_loader import load_memory_context
from components.models.activity import Activity
from components.models.hypothesis import BestHypothesisResult, FixStep
from components.models.kb_entry import KBMatch
from components.models.pillar import PillarResult, ThreePillarSpec, ValidationResult
from components.models.ticket import Ticket
from components.triage.prewarm_cache import PrewarmCache

logger = logging.getLogger("hermits.agent.runner")


class AgentRunResult(BaseModel):
    ticket_id: int
    cache_hit: bool
    pillar_spec: ThreePillarSpec
    best_hypothesis: BestHypothesisResult
    kb_matches: list[KBMatch]
    memory_context_loaded: bool
    safety_checks: list[SafetyCheckResult]
    generated_at: datetime


class Phase1Result(BaseModel):
    ticket_id: int
    cache_hit: bool
    pillar_spec: Optional[ThreePillarSpec] = None
    kb_matches_initial: list[KBMatch]
    memory_context: str
    full_result: Optional[AgentRunResult] = None


class CompletionResult(BaseModel):
    ticket_id: int
    validation_result: ValidationResult
    activity: Activity
    kb_entry_id: str
    all_pillars_passed: bool


_cache = PrewarmCache()


class HermitsAgent:
    def __init__(self):
        self.kb_matcher = KBMatcher()
        self.pillar_gen = ThreePillarsGenerator()
        self.hypo_gen = HypothesisGenerator()
        self.trust = TrustCalibrator()
        self.safety = SafetyLayer()
        self.pillar_validator = PillarValidator()
        self.erp_drafter = ERPDrafter()
        self.kb_writer = KBWriter()
        self.cache = _cache
        self._run_results: dict[int, AgentRunResult] = {}

    def run_ticket_phase1(
        self,
        ticket: Ticket,
        technician_id: str,
    ) -> Phase1Result:
        """
        Fires immediately when technician opens ticket.
        Returns pillar spec so Person A can run SSH recon.
        Also checks prewarm cache — if hit, returns full result immediately.
        """
        if self.cache.is_warm(ticket.id):
            cached = self.cache.get(ticket.id)
            if cached is not None:
                logger.info("Cache hit for ticket %s", ticket.id)
                return Phase1Result(
                    ticket_id=cached.ticket_id,
                    cache_hit=True,
                    pillar_spec=cached.pillar_spec,
                    kb_matches_initial=cached.kb_matches_initial,
                    memory_context=cached.memory_context,
                    full_result=None,
                )

        memory_context = load_memory_context()
        kb_matches = self.kb_matcher.match(ticket, {})
        pillar_spec = self.pillar_gen.generate(ticket, memory_context)

        return Phase1Result(
            ticket_id=ticket.id,
            cache_hit=False,
            pillar_spec=pillar_spec,
            kb_matches_initial=kb_matches,
            memory_context=memory_context,
            full_result=None,
        )

    def run_ticket_phase2(
        self,
        ticket: Ticket,
        recon_output: dict,
        pillar_baseline_results: PillarResult,
        technician_id: str,
        phase1_result: Phase1Result,
    ) -> AgentRunResult:
        """
        Called after Person A returns recon data and pillar baseline.
        Generates the best hypothesis and returns the full result.
        """
        memory_context = phase1_result.memory_context
        memory_context_loaded = bool(memory_context.strip())

        kb_matches = self.kb_matcher.match(ticket, recon_output)

        best_hypothesis_result = self.hypo_gen.generate(
            ticket=ticket,
            recon_output=recon_output,
            pillar_baseline=pillar_baseline_results,
            kb_matches=kb_matches,
            memory_context=memory_context,
        )

        best_hypothesis_result.hypothesis.fix_steps = self.trust.reorder_fix_steps(
            technician_id, best_hypothesis_result.hypothesis.fix_steps
        )

        safety_checks = self._safety_check_all(best_hypothesis_result.hypothesis.fix_steps)

        result = AgentRunResult(
            ticket_id=ticket.id,
            cache_hit=False,
            pillar_spec=phase1_result.pillar_spec,
            best_hypothesis=best_hypothesis_result,
            kb_matches=kb_matches,
            memory_context_loaded=memory_context_loaded,
            safety_checks=safety_checks,
            generated_at=datetime.utcnow(),
        )
        self._run_results[ticket.id] = result
        return result

    def complete_ticket(
        self,
        ticket: Ticket,
        chosen_hypothesis_index: int,
        pillar_after_results: PillarResult,
        executed_steps: list[dict],
        technician_id: str,
        technician_notes: str,
        resolution_time_minutes: int,
        command_decisions: list[tuple[str, bool]],
        pillar_baseline: Optional[PillarResult] = None,
    ) -> CompletionResult:
        run_result = self._run_results.get(ticket.id)
        if run_result is None:
            raise RuntimeError(
                f"No run result for ticket {ticket.id}. Call run_ticket_phase2 first."
            )

        pillar_spec = run_result.pillar_spec
        chosen_hypothesis = run_result.best_hypothesis.hypothesis

        baseline = pillar_baseline or PillarResult(
            service_state_output="(baseline captured at run_ticket)",
            functional_impact_output="(baseline captured at run_ticket)",
            durability_output="(baseline captured at run_ticket)",
        )

        memory_context = load_memory_context()

        validation_result = self.pillar_validator.validate(
            pillar_spec=pillar_spec,
            baseline=baseline,
            after=pillar_after_results,
            ticket=ticket,
            memory_context=memory_context,
        )

        activity = self.erp_drafter.draft(
            ticket=ticket,
            chosen_hypothesis=chosen_hypothesis,
            executed_steps=executed_steps,
            validation_result=validation_result,
            technician_notes=technician_notes,
            memory_context=memory_context,
            start_datetime=run_result.generated_at,
            end_datetime=datetime.utcnow(),
        )

        kb_entry = self.kb_writer.write_resolution(
            ticket=ticket,
            recon_output={},
            chosen_hypothesis=chosen_hypothesis,
            executed_steps=executed_steps,
            validation_result=validation_result,
            technician_id=technician_id,
            resolution_time_minutes=resolution_time_minutes,
        )

        for command, approved in command_decisions:
            self.trust.record_decision(technician_id, command, approved)

        self.cache.invalidate(ticket.id)
        self._run_results.pop(ticket.id, None)

        return CompletionResult(
            ticket_id=ticket.id,
            validation_result=validation_result,
            activity=activity,
            kb_entry_id=kb_entry.id,
            all_pillars_passed=validation_result.overall_passed,
        )

    def _safety_check_all(self, fix_steps: list[FixStep]) -> list[SafetyCheckResult]:
        return [self.safety.check(step.command) for step in fix_steps]
