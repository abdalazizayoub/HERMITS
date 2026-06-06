from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class FixStep(BaseModel):
    command: str
    rationale: str
    risk_level: Literal["low", "medium", "high"]


class Hypothesis(BaseModel):
    hypothesis_title: str
    root_cause_explanation: str
    evidence: list[str]
    fix_steps: list[FixStep]
    expected_pillar_outcomes: dict[str, str]
    confidence_rationale: str


class BestHypothesisResult(BaseModel):
    hypothesis: Hypothesis
    selection_rationale: str
    ticket_id: int
    generated_at: datetime
