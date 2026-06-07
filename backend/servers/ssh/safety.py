import re

BLOCKLIST = [
    (re.compile(r"rm\s+-rf\s+/"), "destructive damage"),
    (re.compile(r"chmod\s+-R\s+777"), "insecure permissions"),
    (re.compile(r"ufw\s+disable"), "disabling firewall"),
    (re.compile(r"DROP\s+DATABASE"), "destructive database operation"),
    (re.compile(r"truncate\s+/var/log"), "log tampering"),
    (re.compile(r"history\s+-c"), "clearing command history"),
    (re.compile(r"chown\s+-R\s+[\w\-:]+\s+(/etc|/var/log|/var/lib|/var/run|/home\b)"), "changing ownership of critical directories"),
]

WARN_LIST = [
    (re.compile(r"systemctl\s+stop"), "stopping system service"),
    (re.compile(r"reboot"), "rebooting system"),
    (re.compile(r"apt\s+remove"), "removing packages"),
]

def safety_check(command: str) -> tuple[bool, str, list[str]]:
    for pattern, reason in BLOCKLIST:
        if pattern.search(command):
            return False, reason, []
    
    warnings = []
    for pattern, reason in WARN_LIST:
        if pattern.search(command):
            warnings.append(reason)

    if warnings:
        return True, "safe with warnings", warnings
    return True, "", []
