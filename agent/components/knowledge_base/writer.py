import logging
import re
from collections import Counter

from components.knowledge_base.store import KBStore
from components.models.hypothesis import Hypothesis
from components.models.kb_entry import KBEntry, ReconFingerprint, TicketFingerprint
from components.models.pillar import ValidationResult
from components.models.ticket import Ticket

logger = logging.getLogger("hermits.knowledge_base.writer")

_ERROR_MARKERS = re.compile(r"(ERROR|FATAL|CRITICAL|Failed|refused|denied|timeout)", re.IGNORECASE)
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "on",
    "at", "for", "with", "from", "by",
}


def _extract_error_patterns(recon_output: dict) -> list[str]:
    logs = recon_output.get("logs", [])
    if isinstance(logs, str):
        lines = logs.splitlines()
    elif isinstance(logs, list):
        lines = [str(l) for l in logs]
    else:
        lines = []

    seen: set[str] = set()
    patterns: list[str] = []
    for line in lines:
        if _ERROR_MARKERS.search(line):
            snippet = line.strip()[:80]
            if snippet not in seen:
                seen.add(snippet)
                patterns.append(snippet)
            if len(patterns) >= 10:
                break
    return patterns


def _extract_symptom_keywords(ticket: Ticket) -> list[str]:
    text = (ticket.title + " " + ticket.description).lower()
    tokens = re.split(r"[^a-z0-9]+", text)
    tokens = [t for t in tokens if t and t not in _STOPWORDS]
    counter = Counter(tokens)
    return [word for word, _ in counter.most_common(15)]


def _failed_services(recon_output: dict) -> list[str]:
    statuses = recon_output.get("service_statuses", {})
    return [
        name
        for name, status in statuses.items()
        if isinstance(status, str) and status.lower() in ("failed", "inactive")
    ]


def _disk_critical(recon_output: dict) -> bool:
    disk = recon_output.get("disk_usage", {})
    if isinstance(disk, str):
        return bool(re.search(r"9[0-9]%|100%", disk))
    if isinstance(disk, dict):
        combined = " ".join(str(v) for v in disk.values())
        return bool(re.search(r"9[0-9]%|100%", combined))
    return False


class KBWriter:
    def __init__(self, store: KBStore | None = None):
        self.store = store or KBStore()

    def write_resolution(
        self,
        ticket: Ticket,
        recon_output: dict,
        chosen_hypothesis: Hypothesis,
        executed_steps: list[dict],
        validation_result: ValidationResult,
        technician_id: str,
        resolution_time_minutes: int,
    ) -> KBEntry:
        error_patterns = _extract_error_patterns(recon_output)
        symptom_keywords = _extract_symptom_keywords(ticket)
        failed_svcs = _failed_services(recon_output)
        top_errors = error_patterns[:5]
        disk_crit = _disk_critical(recon_output)

        fix_commands = [
            step.get("command", "")
            for step in executed_steps
            if step.get("command")
        ]

        erp_snippet = (
            f"Ticket {ticket.id}: {chosen_hypothesis.hypothesis_title}. "
            f"Validation passed: {validation_result.overall_passed}. "
            f"Notes: {validation_result.notes[:200]}"
        )

        entry = KBEntry(
            ticket_fingerprint=TicketFingerprint(
                service_hint=ticket.service_hint,
                error_patterns=error_patterns,
                symptom_keywords=symptom_keywords,
            ),
            recon_fingerprint=ReconFingerprint(
                failed_services=failed_svcs,
                top_errors=top_errors,
                disk_critical=disk_crit,
            ),
            root_cause=chosen_hypothesis.root_cause_explanation,
            fix_commands=fix_commands,
            validation_passed=validation_result.overall_passed,
            resolution_time_minutes=resolution_time_minutes,
            technician_id=technician_id,
            erp_log_snippet=erp_snippet,
        )
        self.store.append(entry)
        logger.info("KB entry %s written for ticket %s", entry.id, ticket.id)
        return entry
