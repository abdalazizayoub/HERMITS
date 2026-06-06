from datetime import datetime
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class TicketFingerprint(BaseModel):
    service_hint: Optional[str]
    error_patterns: list[str]
    symptom_keywords: list[str]


class ReconFingerprint(BaseModel):
    failed_services: list[str]
    top_errors: list[str]
    disk_critical: bool


class KBEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ticket_fingerprint: TicketFingerprint
    recon_fingerprint: ReconFingerprint
    root_cause: str
    fix_commands: list[str]
    validation_passed: bool
    resolution_time_minutes: int
    technician_id: str
    erp_log_snippet: str


class KBMatch(BaseModel):
    entry: KBEntry
    similarity_score: float
    confidence_boost: float
