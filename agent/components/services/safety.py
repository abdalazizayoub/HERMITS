import re
import logging
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger("hermits.agent.safety")

BLOCKED_PATTERNS = [
    (r"rm\s+-rf\s+/(?!(var/log|tmp|var/cache))", "rm -rf on system path"),
    (r"dd\s+.*of=/dev/", "dd write to device"),
    (r"mkfs", "filesystem format command"),
    (r">\s*/dev/sd", "direct block device write"),
    (r"chmod\s+-R\s+777\s+/", "chmod 777 recursive on root"),
    (r"chmod\s+777\s+/(etc|var|home|srv|bin|usr)", "chmod 777 on system directory"),
    (r"DROP\s+(TABLE|DATABASE)", "SQL drop statement"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "system shutdown command"),
    (
        r"(ufw\s+disable|iptables\s+-F|systemctl\s+(stop|disable)\s+(ufw|firewalld|fail2ban|auditd))",
        "disabling security service",
    ),
    (r"rm\s+.*-r.*\s+/(etc|home|var/lib/postgresql|srv)\b", "deleting critical directory"),
    (r"cat\s+.*\.(pem|key|p12|pfx)", "reading private key file"),
]

_COMPILED = [(re.compile(pat, re.IGNORECASE), reason) for pat, reason in BLOCKED_PATTERNS]

# Matches hardcoded secret values (not variable references like $PASSWORD)
_SECRET_PATTERN = re.compile(
    r"(password|token|secret|passwd|api_key)\s*=\s*(?!\$)[^\s]+"
    r"|mysql\b.*\s-p(?!\s|\$)[^\s]+",
    re.IGNORECASE,
)


class SafetyCheckResult(BaseModel):
    safe: bool
    reason: Optional[str] = None


class SafetyLayer:
    def check(self, command: str) -> SafetyCheckResult:
        for compiled, reason in _COMPILED:
            if compiled.search(command):
                logger.warning("Blocked command [%s]: %s", reason, command[:80])
                return SafetyCheckResult(safe=False, reason=reason)

        if _SECRET_PATTERN.search(command):
            logger.warning("Blocked command: contains hardcoded secret")
            return SafetyCheckResult(safe=False, reason="command contains hardcoded secret")

        return SafetyCheckResult(safe=True)
