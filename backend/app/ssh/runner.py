import asyncio
import os
import asyncssh
from app.ssh.safety import safety_check

KEY_DIR = "/keys"
DEFAULT_USER = os.environ.get("SSH_USERNAME", "azureuser")
TIMEOUT = int(os.environ.get("SSH_TIMEOUT", "30"))

def get_key_path(ticket_id: int) -> str:
    key_id = ticket_id % 10
    return f"{KEY_DIR}/case{key_id}_key.pem"

async def run_recon(host: str, port: int, username: str, key_path: str) -> dict[str, str]:
    READ_ONLY = {
        "disk":         "df -h",
        "disk_inodes":  "df -i",
        "memory":       "free -h",
        "uptime":       "uptime",
        "failed_units": "systemctl list-units --state=failed --no-pager",
        "journal_err":  "journalctl -p err -n 50 --no-pager",
        "processes":    "ps aux --sort=-%mem | head -20",
        "ports":        "ss -tlnp",
        "timers":       "systemctl list-timers --no-pager",
        "cron":         "cat /etc/crontab",
        "last_logins":  "last -n 10",
        "service_files": "find /etc/systemd /lib/systemd -name '*.service' 2>/dev/null | xargs grep -l '8080' 2>/dev/null",
        "opt_files":     "ls /opt/hackathon/ 2>/dev/null",
        "all_services":  "systemctl list-unit-files --type=service --no-pager | grep -v disabled | head -40",
    }
    results = {}
    try:
        async with asyncssh.connect(
            host,
            port=port,
            username=username,
            client_keys=[key_path],
            known_hosts=None
        ) as conn:
            for name, cmd in READ_ONLY.items():
                try:
                    result = await asyncio.wait_for(
                        conn.run(cmd),
                        timeout=TIMEOUT
                    )
                    results[name] = result.stdout.strip()
                except asyncio.TimeoutError:
                    results[name] = "TIMEOUT"
                except Exception as e:
                    results[name] = f"ERROR: {str(e)}"
    except asyncssh.Error as conn_err:
        return {"error": f"Connection failed: {str(conn_err)}"}
    return results

async def run_command(host: str, port: int, username: str, key_path: str, command: str) -> dict:
    is_safe, reason, warnings = safety_check(command=command)
    if not is_safe:
        return {
            "blocked": True,
            "reason": reason,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "warnings": warnings,
            "ok": False,
        }
    try:
        async with asyncssh.connect(
            host,
            port=port,
            username=username,
            client_keys=[key_path],
            known_hosts=None
        ) as conn:
            result = await asyncio.wait_for(
                conn.run(command),
                timeout=TIMEOUT
            )
            return {
                "blocked": False,
                "reason": reason,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.exit_status,
                "warnings": warnings,
                "ok": result.exit_status == 0,
            }
    except asyncio.TimeoutError:
        return {
            "blocked": False,
            "reason": reason,
            "stdout": "",
            "stderr": "Command timed out",
            "exit_code": None,
            "warnings": warnings,
            "ok": False,
        }
    except asyncssh.Error as conn_err:
        return {
            "blocked": False,
            "reason": reason,
            "stdout": "",
            "stderr": f"Connection failed: {str(conn_err)}",
            "exit_code": None,
            "warnings": warnings,
            "ok": False,
        }
    
async def run_validation(host: str, port: int, username: str, key_path: str) -> dict:
    command = "sudo /opt/hackathon/public-test.sh"
    try:
        async with asyncssh.connect(
            host,
            port=port,
            username=username,
            client_keys=[key_path],
            known_hosts=None
        ) as conn:
            result = await asyncio.wait_for(
                conn.run(command),
                timeout=TIMEOUT
            )
            return {
                "passed": result.exit_status == 0,
                "output": result.stdout.strip()
            }
    except asyncio.TimeoutError:
        return {
            "passed": False,
            "output": "Validation command timed out"
        }
    except asyncssh.Error as conn_err:
        return {
            "passed": False,
            "output": f"Connection failed: {str(conn_err)}"
        }