import json, re, uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("audit_logs")
LOG_DIR.mkdir(exist_ok=True)

SECRET_PATTERN = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-_]+"),  # Bearer tokens
    re.compile(r"password\s*=\s*['\"]?[^'\"\s]+['\"]?", re.IGNORECASE),  # password=secret
    re.compile(r"key_path\s*=\s*['\"]?[^'\"\s]+['\"]?", re.IGNORECASE),  # key_path=/path/to/key.pem
]

def _redact(text: str) -> str:
    for pattern in SECRET_PATTERN:
        text = pattern.sub("[REDACTED]", text)
    return text

class AuditLogger:
    def __init__(self, ticket_id: int):
        self.ticket_id  = ticket_id
        self.session_id = str(uuid.uuid4())[:8]
        self.entries: list[dict] = []
        self._file = LOG_DIR / f"ticket_{ticket_id}_{self.session_id}.jsonl"

    def log(self, actor: str, category: str, action: str,
            command="", result="", exit_code=None) -> dict:
        entry_dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "category": category,
            "action": action,
            "command": _redact(command),
            "result": _redact(result),
            "exit_code": exit_code,
        }
        self.entries.append(entry_dict)
        with self._file.open("a") as f:
            f.write(json.dumps(entry_dict) + "\n")
        return entry_dict


    def as_commands_summary(self) -> str:
        summary = []
        for entry in self.entries:
            if entry["category"] == "execution":
                status = "ok" if entry["exit_code"] == 0 else f"exit={entry['exit_code']}"
                summary.append(f"{entry['command']} → {status}")
        return "\n".join(summary) if summary else "No commands executed."

_sessions: dict[int, AuditLogger] = {}

def get_logger(ticket_id: int) -> AuditLogger:
    if ticket_id not in _sessions:
        _sessions[ticket_id] = AuditLogger(ticket_id)
    return _sessions[ticket_id]

def close_session(ticket_id: int) -> None:
    _sessions.pop(ticket_id, None)