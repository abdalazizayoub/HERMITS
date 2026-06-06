import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from components.services.safety import SafetyCheckResult

logger = logging.getLogger("hermits.audit_log")

DATA_DIR = os.getenv("HERMITS_DATA_DIR", "./data")


class AuditLog:
    """Append-only JSONL log at data/audit_{date}.jsonl"""

    def _log_path(self, date_str: str) -> Path:
        path = Path(DATA_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path / f"audit_{date_str}.jsonl"

    def _write(self, entry: dict) -> None:
        date_str = entry["timestamp"][:10]
        log_path = self._log_path(date_str)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_command(
        self,
        ticket_id: str,
        technician_id: str,
        command: str,
        approved: bool,
        output: Optional[str],
        safety_result: SafetyCheckResult,
        timestamp: Optional[datetime] = None,
    ) -> None:
        ts = (timestamp or datetime.utcnow()).isoformat()
        entry = {
            "timestamp": ts,
            "ticket_id": ticket_id,
            "technician_id": technician_id,
            "event_type": "command",
            "command": command,
            "approved": approved,
            "safety_passed": safety_result.safe,
            "safety_reason": safety_result.reason,
        }
        # Only include output when caller explicitly passes it (post-scrub)
        if output is not None:
            entry["output"] = output
        self._write(entry)

    def log_event(
        self,
        ticket_id: str,
        event_type: str,
        details: dict,
        timestamp: Optional[datetime] = None,
    ) -> None:
        ts = (timestamp or datetime.utcnow()).isoformat()
        entry = {
            "timestamp": ts,
            "ticket_id": ticket_id,
            "technician_id": details.get("technician_id", ""),
            "event_type": event_type,
            "command": "",
            "approved": None,
            "safety_passed": None,
            "safety_reason": None,
            **details,
        }
        self._write(entry)

    def get_for_ticket(self, ticket_id: str) -> list[dict]:
        results = []
        data_path = Path(DATA_DIR)
        if not data_path.exists():
            return results
        for log_file in sorted(data_path.glob("audit_*.jsonl")):
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("ticket_id") == ticket_id:
                            results.append(entry)
                    except json.JSONDecodeError:
                        logger.warning("Corrupt audit line in %s", log_file)
        return results
