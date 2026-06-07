import asyncio
import os
import asyncssh
from ssh.safety import safety_check

ROOT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
)
KEY_DIR = os.environ.get("SSH_KEY_DIR", os.path.join(ROOT_DIR, "keys"))
DEFAULT_USER = os.environ.get("SSH_USERNAME", "azureuser")
TIMEOUT = int(os.environ.get("SSH_TIMEOUT", "15"))
COMMAND_TIMEOUT = int(os.environ.get("SSH_COMMAND_TIMEOUT", "45"))
VALIDATION_TIMEOUT = int(os.environ.get("SSH_VALIDATION_TIMEOUT", "300"))

COMMON_READ_ONLY = {
    "disk":         "df -h",
    "disk_inodes":  "df -i",
    "memory":       "free -h",
    "uptime":       "uptime",
    "failed_units": "systemctl list-units --state=failed --no-pager | head -40",
    "processes":    "ps aux --sort=-%mem | head -20",
    "ports":        "ss -tlnp | head -50",
    "service_users": "find /etc/systemd/system /lib/systemd/system -name '*.service' 2>/dev/null | xargs grep -i 'User=' 2>/dev/null | head -50",
    "hosts_file":   "cat /etc/hosts",
}

OPTIONAL_READ_ONLY = {
    "service_files": "find /etc/systemd /lib/systemd -name '*.service' 2>/dev/null | xargs grep -l 'EnvironmentFile\|ExecStart' 2>/dev/null | head -20",
    "app_configs":   "find /etc /opt /srv /var/www -maxdepth 5 -type f \( -name '*.env' -o -name '*.conf' -o -name '*.cfg' -o -name '*.ini' \) 2>/dev/null | xargs grep -iE 'port|bind|listen|upload|document|path|host|url' 2>/dev/null | head -50",
    "upload_dirs":   "find /var/www /opt /srv /home -type d \( -name 'upload*' -o -name 'document*' -o -name 'media' -o -name 'files' \) 2>/dev/null | xargs ls -la 2>/dev/null | head -20",
    "dns_resolution": "grep -RhE 'host|HOST|endpoint|ENDPOINT|url|URL' /opt /srv /var/www /etc 2>/dev/null | grep -v '#' | head -20",
    "listening_ports": "ss -tulpn 2>/dev/null | head -50",
    "port_mismatch": "ss -tlnp 2>/dev/null | awk '{print $5}' | grep -oP ':\\K[0-9]+' | sort -un | uniq | head -50",
    "pg_users":      "sudo -n -u postgres psql -c '\\du' 2>/dev/null || echo 'pg not accessible'",
    "pg_grants":     "sudo -n -u postgres psql -c \"SELECT grantee, table_name, string_agg(privilege_type, ', ') FROM information_schema.role_table_grants WHERE table_schema='public' GROUP BY grantee, table_name ORDER BY table_name;\" 2>/dev/null || echo 'no grants'",
    "pg_seq_grants": "sudo -n -u postgres psql -c \"SELECT relname AS sequence, relacl FROM pg_class WHERE relkind='S' ORDER BY relname;\" 2>/dev/null || echo 'no seq info'",
    "pg_databases":  "sudo -n -u postgres psql -c '\\l' 2>/dev/null || echo 'no db list'",
}

HINT_COMMANDS = {
    "nginx": ["app_configs", "service_files", "upload_dirs", "listening_ports", "port_mismatch"],
    "apache": ["app_configs", "service_files", "upload_dirs", "listening_ports", "port_mismatch"],
    "httpd": ["app_configs", "service_files", "upload_dirs", "listening_ports", "port_mismatch"],
    "postgres": ["pg_users", "pg_grants", "pg_seq_grants", "pg_databases"],
    "postgresql": ["pg_users", "pg_grants", "pg_seq_grants", "pg_databases"],
    "mysql": ["pg_users", "pg_grants", "pg_seq_grants", "pg_databases"],
    "mariadb": ["pg_users", "pg_grants", "pg_seq_grants", "pg_databases"],
    "database": ["pg_users", "pg_grants", "pg_seq_grants", "pg_databases"],
    "upload": ["upload_dirs", "app_configs"],
    "file upload": ["upload_dirs", "app_configs"],
    "dns": ["hosts_file", "dns_resolution"],
    "hostname": ["hosts_file", "dns_resolution"],
    "port": ["listening_ports", "port_mismatch", "app_configs"],
}


def get_key_path(ticket_id: int) -> str:
    key_id = ticket_id % 10
    return os.path.join(KEY_DIR, f"case{key_id}_key.pem")

async def _run_one(conn: asyncssh.SSHClientConnection, name: str, cmd: str, timeout: int) -> tuple[str, str]:
    try:
        result = await asyncio.wait_for(conn.run(cmd), timeout=timeout)
        return name, result.stdout.strip()
    except asyncio.TimeoutError:
        return name, "TIMEOUT"
    except Exception as e:
        return name, f"ERROR: {str(e)}"


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
        "service_files": "find /etc/systemd /lib/systemd -name '*.service' 2>/dev/null | xargs grep -l 'EnvironmentFile\\|ExecStart' 2>/dev/null | head -10",
        "opt_files":     "ls /opt/ 2>/dev/null",
        "all_services":  "systemctl list-unit-files --type=service --no-pager | grep -v disabled | head -40",
        # env / config files — generalised, no hardcoded service name
        "env_files":           "find /etc /opt /srv -name '*.env' -o -name '*.conf' -o -name '*.cfg' 2>/dev/null | grep -v proc | head -20",
        "env_contents":        "find /etc -name '*.env' 2>/dev/null | xargs cat 2>/dev/null | head -100",
        "app_configs":         "find /opt /srv /app -name '*.env' -o -name 'config.*' -o -name '*.cfg' -o -name '*.ini' 2>/dev/null | xargs cat 2>/dev/null | head -100",
        # read every service unit that declares an EnvironmentFile — no hardcoded name
        "service_env_files":   "find /etc/systemd -name '*.service' 2>/dev/null | xargs grep -l 'EnvironmentFile' 2>/dev/null | xargs systemctl cat 2>/dev/null | head -150",
        "all_env_file_values": "find /etc/systemd -name '*.service' 2>/dev/null | xargs grep -h 'EnvironmentFile' 2>/dev/null | awk '{print $NF}' | sort -u | xargs cat 2>/dev/null | head -100",
        # port / network
        "listening_ports":     "ss -tulpn 2>/dev/null",
        "port_mismatch":       "ss -tulpn 2>/dev/null | awk '{print $5}' | grep -oP ':\\K[0-9]+' | sort -un",
        # permissions — find actual upload/document directories and their owner
        "upload_dirs":         "find /var/www /opt /srv /home -type d \\( -name 'upload*' -o -name 'document*' -o -name 'media' -o -name 'files' \\) 2>/dev/null | xargs ls -la 2>/dev/null | head -30",
        "service_users":       "find /etc/systemd/system -name '*.service' 2>/dev/null | xargs grep -i 'user=\\|group=' 2>/dev/null",
        # read application source for hardcoded paths / constants
        "app_source":          "find /opt /srv /var/www -maxdepth 5 \\( -name 'app.py' -o -name 'main.py' -o -name 'server.py' -o -name 'config.py' -o -name 'settings.py' \\) 2>/dev/null | head -3 | xargs cat 2>/dev/null | head -200",
        "upload_config":       "find /opt /srv /var/www -maxdepth 5 \\( -name 'app.py' -o -name 'main.py' -o -name 'server.py' -o -name 'config.py' -o -name 'settings.py' \\) 2>/dev/null | head -3 | xargs grep -in 'upload\\|UPLOAD\\|document\\|path\\|folder\\|directory\\|PORT\\|BIND' 2>/dev/null | head -50",
        # DNS / network reachability
        "hosts_file":          "cat /etc/hosts",
        "dns_resolution":      "cat /etc/hosts && echo '---' && grep -rh 'host\\|HOST\\|endpoint\\|ENDPOINT\\|url\\|URL' /opt /srv /var/www /etc --include='*.env' --include='*.cfg' --include='*.ini' 2>/dev/null | grep -v '#' | head -20",
        "firewall":            "sudo -n ufw status 2>/dev/null || sudo -n iptables -L -n 2>/dev/null | head -20",
        # postgres — roles, table grants, and sequence grants (INSERT needs sequences too)
        "pg_users":            "sudo -n -u postgres psql -c '\\du' 2>/dev/null || echo 'pg not accessible'",
        "pg_grants":           "sudo -n -u postgres psql -c \"SELECT grantee, table_name, string_agg(privilege_type, ', ') FROM information_schema.role_table_grants WHERE table_schema='public' GROUP BY grantee, table_name ORDER BY table_name;\" 2>/dev/null || echo 'no grants'",
        "pg_seq_grants":       "sudo -n -u postgres psql -c \"SELECT relname AS sequence, relacl FROM pg_class WHERE relkind='S' ORDER BY relname;\" 2>/dev/null || echo 'no seq info'",
        "pg_databases":        "sudo -n -u postgres psql -c '\\l' 2>/dev/null || echo 'no db list'",
        # monitoring / collector — check ALL states, not just active
        "collector_status":    "systemctl list-unit-files --type=service 2>/dev/null | grep -iE 'collect|monitor|metric|agent|telegraf|prometheus|fluentd|filebeat|log' | head -10",
        "collector_detail":    "systemctl list-units --type=service --all --no-pager 2>/dev/null | grep -iE 'collect|monitor|metric|agent|telegraf|prometheus|fluentd|filebeat|log' | head -10",
        # recent journal logs from collector services — reveals permission errors, connection refused, missing files
        "collector_logs":      "systemctl list-units --type=service --all --no-pager 2>/dev/null | grep -iE 'collect|monitor|metric|agent|telegraf|prometheus|fluentd|filebeat' | awk '{print $1}' | grep '\\.service$' | head -5 | while read svc; do echo \"=== $svc ===\"; journalctl -u \"$svc\" -n 15 --no-pager 2>/dev/null; done | head -100",
        # /var/lib ownership — app data dirs live here; root-owned + non-root service = permission block
        "var_lib_perms":       "ls -la /var/lib/ 2>/dev/null | head -25",
        "case_json":     "cat /opt/hackathon/case.json 2>/dev/null",
        "public_test":   "cat /opt/hackathon/public-test.sh 2>/dev/null",
        "service_logs_metrics": "journalctl -u metrics-agent -u metrics-ingest -n 15 --no-pager 2>/dev/null",
        "service_show":         "systemctl show metrics-agent metrics-ingest 2>/dev/null | grep -E 'Environment|ExecStart|User|State'",
    }
    # OpenSSH default MaxSessions is 10; batch to stay safely under the limit
    _BATCH = 8
    # Retry connect up to 3 times with backoff — the VM may be briefly unreachable
    # after a service restart or the pillar baseline triggered a reboot check.
    _CONNECT_ATTEMPTS = 3
    _CONNECT_RETRY_DELAY = 20  # seconds between attempts

    for attempt in range(_CONNECT_ATTEMPTS):
        try:
            async with asyncssh.connect(
                host,
                port=port,
                username=username,
                client_keys=[key_path],
                known_hosts=None,
                connect_timeout=15,
            ) as conn:
                items = list(READ_ONLY.items())
                results: dict[str, str] = {}
                for i in range(0, len(items), _BATCH):
                    batch = items[i : i + _BATCH]
                    pairs = await asyncio.gather(
                        *[_run_one(conn, name, cmd, TIMEOUT) for name, cmd in batch]
                    )
                    results.update(pairs)
                return results
        except (asyncssh.Error, OSError, Exception) as conn_err:
            if attempt < _CONNECT_ATTEMPTS - 1:
                await asyncio.sleep(_CONNECT_RETRY_DELAY)
            else:
                return {"error": f"Connection failed after {_CONNECT_ATTEMPTS} attempts: {str(conn_err)}"}
    return {"error": "Recon failed: unreachable after all retries"}

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
    if command.startswith("sudo ") and not command.startswith("sudo -n "):
        command = command.replace("sudo ", "sudo -n ", 1)
    # public-test.sh is a slow integration test; give it more time
    cmd_timeout = 120 if "public-test.sh" in command else COMMAND_TIMEOUT
    try:
        async with asyncssh.connect(
            host,
            port=port,
            username=username,
            client_keys=[key_path],
            known_hosts=None,
            connect_timeout=30,
        ) as conn:
            # sudo needs a PTY on Ubuntu VMs (PAM/requiretty); other commands must NOT
            # use a PTY because `xargs grep` with no input reads from PTY stdin and hangs.
            use_pty = "sudo" in command
            result = await asyncio.wait_for(
                conn.run(command, request_pty=use_pty),
                timeout=cmd_timeout
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
            "stderr": f"Command timed out after {cmd_timeout}s",
            "exit_code": 124,
            "warnings": warnings,
            "ok": False,
        }
    except (asyncssh.DisconnectError, ConnectionResetError) as disc_err:
        return {
            "blocked": False,
            "reason": reason,
            "stdout": "",
            "stderr": f"SSH connection dropped: {str(disc_err)}",
            "exit_code": 255,
            "warnings": warnings,
            "ok": False,
        }
    except asyncssh.Error as conn_err:
        return {
            "blocked": False,
            "reason": reason,
            "stdout": "",
            "stderr": f"SSH error: {str(conn_err)}",
            "exit_code": 255,
            "warnings": warnings,
            "ok": False,
        }
    except Exception as exc:
        return {
            "blocked": False,
            "reason": reason,
            "stdout": "",
            "stderr": f"Unexpected error: {str(exc)}",
            "exit_code": 255,
            "warnings": warnings,
            "ok": False,
        }
    
async def run_pillar_baseline(
    host: str, port: int, username: str, key_path: str,
    service_state_cmd: str, functional_impact_cmd: str, durability_cmd: str,
) -> tuple[dict, dict, dict]:
    """Run the 3 pillar baseline commands over a SINGLE SSH connection in parallel.
    Falls back to individual run_command calls if the shared connection fails."""
    try:
        async with asyncssh.connect(
            host, port=port, username=username,
            client_keys=[key_path], known_hosts=None, connect_timeout=15,
        ) as conn:
            results = await asyncio.gather(
                _run_one(conn, "svc", service_state_cmd, TIMEOUT),
                _run_one(conn, "func", functional_impact_cmd, TIMEOUT),
                _run_one(conn, "dur", durability_cmd, TIMEOUT),
            )
            def _to_dict(output: str) -> dict:
                return {"stdout": output, "stderr": "", "exit_code": 0, "blocked": False, "ok": True, "reason": "", "warnings": []}
            return _to_dict(results[0][1]), _to_dict(results[1][1]), _to_dict(results[2][1])
    except Exception:
        # Shared connection failed — fall back to independent commands
        svc, func, dur = await asyncio.gather(
            run_command(host, port, username, key_path, service_state_cmd),
            run_command(host, port, username, key_path, functional_impact_cmd),
            run_command(host, port, username, key_path, durability_cmd),
        )
        return svc, func, dur


async def run_validation(host: str, port: int, username: str, key_path: str) -> dict:
    command = "sudo -n /opt/hackathon/public-test.sh"
    try:
        async with asyncssh.connect(
            host,
            port=port,
            username=username,
            client_keys=[key_path],
            known_hosts=None,
            connect_timeout=15,
        ) as conn:
            result = await asyncio.wait_for(
                conn.run(command),
                timeout=VALIDATION_TIMEOUT
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