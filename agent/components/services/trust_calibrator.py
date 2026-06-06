import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from components.models.hypothesis import FixStep

logger = logging.getLogger("hermits.agent.trust_calibrator")

DATA_DIR = os.getenv("HERMITS_DATA_DIR", "./data")

CATEGORIES: dict[str, str] = {
    "systemctl_restart": r"systemctl\s+(restart|start)\b",
    "systemctl_stop": r"systemctl\s+(stop|disable)\b",
    "apt_install": r"apt(-get)?\s+install\b",
    "file_edit": r"(sed\s|awk\s|tee\s|echo\s+.+>>?)",
    "log_rotation": r"(logrotate|truncate)\b",
    "disk_cleanup": r"(find\s.+\-delete|rm\s+-rf\s+/var/log)",
    "process_kill": r"(kill|pkill|killall)\b",
    "cert_renewal": r"(certbot|openssl\s+req)\b",
    "config_reload": r"(nginx\s+-s\s+reload|apache2ctl|systemctl\s+reload)\b",
}

_COMPILED_CATEGORIES = {
    name: re.compile(pattern, re.IGNORECASE) for name, pattern in CATEGORIES.items()
}

_HIGH_RISK_CATEGORIES = {"systemctl_stop", "disk_cleanup", "process_kill"}


class TrustCalibrator:
    def _trust_path(self, technician_id: str) -> Path:
        path = Path(DATA_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path / f"trust_{technician_id}.json"

    def _load(self, technician_id: str) -> dict:
        p = self._trust_path(technician_id)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self, technician_id: str, data: dict) -> None:
        p = self._trust_path(technician_id)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def classify(self, command: str) -> str:
        for name, compiled in _COMPILED_CATEGORIES.items():
            if compiled.search(command):
                return name
        return "other"

    def record_decision(self, technician_id: str, command: str, approved: bool) -> None:
        category = self.classify(command)
        data = self._load(technician_id)
        if category not in data:
            data[category] = {"approved": 0, "rejected": 0}
        if approved:
            data[category]["approved"] += 1
        else:
            data[category]["rejected"] += 1
        self._save(technician_id, data)

    def _approval_rate(self, stats: dict) -> Optional[float]:
        total = stats.get("approved", 0) + stats.get("rejected", 0)
        if total == 0:
            return None
        return stats.get("approved", 0) / total

    def reorder_fix_steps(self, technician_id: str, fix_steps: list[FixStep]) -> list[FixStep]:
        data = self._load(technician_id)
        normal: list[tuple[FixStep, float]] = []
        demoted: list[FixStep] = []

        for step in fix_steps:
            category = self.classify(step.command)
            stats = data.get(category, {})
            rate = self._approval_rate(stats)
            total = stats.get("approved", 0) + stats.get("rejected", 0)

            if rate is None:
                # Unknown / no history — keep original order at neutral rate 0.5
                normal.append((step, 0.5))
                continue

            # High-risk categories always demoted if rate < 0.5 regardless of count
            if category in _HIGH_RISK_CATEGORIES and rate < 0.5:
                demoted.append(step)
                continue

            # Any category with rate < 0.4 AND more than 3 decisions moves to end
            if rate < 0.4 and total > 3:
                demoted.append(step)
                continue

            normal.append((step, rate))

        normal.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in normal] + demoted

    def get_trust_summary(self, technician_id: str) -> dict:
        data = self._load(technician_id)
        summary = {}
        for category, stats in data.items():
            rate = self._approval_rate(stats)
            summary[category] = {
                **stats,
                "approval_rate": rate,
            }
        return summary
