from typing import Optional
from pydantic import BaseModel


class ThreePillarSpec(BaseModel):
    service_state_cmd: str
    functional_impact_cmd: str
    durability_cmd: str
    definition_of_done: str


class PillarResult(BaseModel):
    service_state_output: str
    functional_impact_output: str
    durability_output: str
    service_state_passed: Optional[bool] = None
    functional_impact_passed: Optional[bool] = None
    durability_passed: Optional[bool] = None
    overall_passed: Optional[bool] = None


class ValidationResult(BaseModel):
    service_state_passed: bool
    functional_impact_passed: bool
    durability_passed: bool
    overall_passed: bool
    notes: str
