import asyncio
import os
import asyncssh
from ssh.safety import safety_check

ROOT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
)
KEY_DIR = os.environ.get("SSH_KEY_DIR", os.path.join(ROOT_DIR, "keys"))
DEFAULT_USER = os.environ.get("SSH_USERNAME", "azureuser")
TIMEOUT = int(os.environ.get("SSH_TIMEOUT", "30"))

def get_key_path(ticket_id: int) -> str:
    key_id = ticket_id % 10
    return os.path.join(KEY_DIR, f"case{key_id}_key.pem")

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
        "env_files":        "find /etc /opt /srv -name '*.env' -o -name '*.conf' -o -name '*.cfg' 2>/dev/null | grep -v proc | head -20",
        "env_contents":     "find /etc -name '*.env' 2>/dev/null | xargs cat 2>/dev/null | head -100",
        "service_env":      "systemctl show customer-status.service 2>/dev/null | grep -i 'environment\|envfile\|execstart' || systemctl list-units --type=service --state=active --no-pager | head -20",
        "app_configs":      "find /opt /srv /app -name '*.env' -o -name 'config.*' -o -name '*.cfg' -o -name '*.ini' 2>/dev/null | xargs cat 2>/dev/null | head -100",
        "listening_ports":  "ss -tulpn 2>/dev/null",
        "service_env_files":"systemctl cat customer-status.service 2>/dev/null || find /etc/systemd -name '*.service' 2>/dev/null | xargs grep -l 'EnvironmentFile' 2>/dev/null | xargs cat 2>/dev/null",
        "port_mismatch":    "ss -tulpn | awk '{print $5}' | grep -oP ':\\K[0-9]+' | sort -u",
        "upload_dirs":      "find /var/www /opt /srv -type d \\( -name 'upload*' -o -name 'document*' \\) 2>/dev/null | xargs ls -la 2>/dev/null | head -20",
        "service_users":    "find /etc/systemd/system -name '*.service' | xargs grep -i 'user=' 2>/dev/null",
        "hosts_file":       "cat /etc/hosts",
        "dns_resolution":   "getent hosts partner-api.internal 2>/dev/null || echo 'not resolved'",
        "firewall":         "sudo ufw status 2>/dev/null || sudo iptables -L -n 2>/dev/null | head -20",
        "pg_users":         "sudo -u postgres psql -c '\\du' 2>/dev/null || echo 'pg not accessible'",
        "pg_tables":        "sudo -u postgres psql -c '\\dt' 2>/dev/null || echo 'no tables'",
        "pg_grants":        "sudo -u postgres psql -c '\\dp' 2>/dev/null || echo 'no grants'",
        "collector_status": "systemctl status --no-pager $(systemctl list-units --type=service --state=active | grep -i 'collect\\|monitor\\|metric\\|agent' | awk '{print $1}') 2>/dev/null | head -30",
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
    # Prevent the SSH session from hanging on slow-starting services
    if "systemctl start " in command and "--no-block" not in command:
        command = command.replace("systemctl start ", "systemctl start --no-block ")
    if "systemctl restart " in command and "--no-block" not in command:
        command = command.replace("systemctl restart ", "systemctl restart --no-block ")
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