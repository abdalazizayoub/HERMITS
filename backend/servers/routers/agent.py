from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from erp import client as erp
from ssh import runner as ssh
from audit import logger as audit_mod

router = APIRouter()

_sessions: dict[int, dict] = {}


def adapt_recon_for_agent(recon: dict) -> dict:
    def ensure_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    return {
        "logs": recon.get("journal_err", ""),
        "service_statuses": recon.get("failed_units", ""),
        "disk_usage": {
            "disk": recon.get("disk"),
            "disk_inodes": recon.get("disk_inodes"),
        },
        "processes": recon.get("processes", []),
        "cron_timers": ensure_list(recon.get("timers")) + ensure_list(recon.get("cron")),
        "ports": recon.get("ports", []),
        "config_files": (
            recon.get("env_contents", "") + "\n" +
            recon.get("all_env_file_values", "") + "\n" +
            recon.get("app_configs", "") + "\n" +
            recon.get("service_env_files", "")
        ),
        "port_config": recon.get("listening_ports", "") + "\n" + recon.get("port_mismatch", ""),
        "service_units": recon.get("service_env_files", ""),
        "upload_dirs": recon.get("upload_dirs", ""),
        "service_users": recon.get("service_users", ""),
        "app_source": recon.get("app_source", "") + "\n" + recon.get("upload_config", ""),
        "network": (
            recon.get("hosts_file", "") + "\n" +
            recon.get("dns_resolution", "") + "\n" +
            recon.get("firewall", "")
        ),
        "database": (
            recon.get("pg_users", "") + "\n" +
            recon.get("pg_grants", "") + "\n" +
            recon.get("pg_seq_grants", "") + "\n" +
            recon.get("pg_databases", "")
        ),
        "collector": recon.get("collector_status", ""),
        "collector_detail": recon.get("collector_detail", ""),
        "raw": recon,
    }


class ReconRequest(BaseModel):
    ticket_id: int

class ExecuteRequest(BaseModel):
    ticket_id: int
    command:   str
    category:  str

class ValidateRequest(BaseModel):
    ticket_id: int


class ResetSessionRequest(BaseModel):
    ticket_id: int


@router.post("/recon")
async def run_recon(req: ReconRequest):
    # Step 1: fetch SSH details from ERP — this MUST succeed.
    try:
        system_data = await erp.get_customer_system(ticket_id=req.ticket_id)
        system   = system_data["system"]
        host     = system["ip"]
        port     = system.get("port", 22)
        username = system["username"]
        key_path = ssh.get_key_path(req.ticket_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERP unavailable: {repr(e)}")

    # Step 2: register session BEFORE SSH recon so execute/validate always work.
    _sessions[req.ticket_id] = {
        "host": host, "port": port, "username": username, "key_path": key_path,
        "recon": {}, "recon_adapted": {},
    }

    # Step 3: run SSH recon — returns a dict, handles its own failures, never raises.
    recon_results = await ssh.run_recon(host, port, username, key_path)
    adapted = adapt_recon_for_agent(recon_results)
    _sessions[req.ticket_id]["recon"]         = recon_results
    _sessions[req.ticket_id]["recon_adapted"] = adapted

    ssh_ok = "error" not in recon_results
    try:
        audit_logger = audit_mod.get_logger(req.ticket_id)
        audit_logger.log(
            actor="system",
            category="recon",
            action="run_recon",
            command=f"ssh recon on {host}:{port} as {username}",
            result=f"{'ok' if ssh_ok else 'failed'}, {len(recon_results)} keys",
        )
    except Exception:
        pass

    return {"recon": recon_results, "recon_adapted": adapted, "ssh_ok": ssh_ok}


@router.post("/execute")
async def execute_command(req: ExecuteRequest):
    session = _sessions.get(req.ticket_id)
    if not session:
        raise HTTPException(status_code=400, detail="Session not found — run recon first")
    audit_logger = audit_mod.get_logger(req.ticket_id)
    try:
        audit_logger.log(
            actor="human",
            category="approval",
            action="approve_command",
            command=req.command,
        )
        # If the previous command timed out the connection may be stale — refresh session
        if session.get("reconnect"):
            try:
                fresh = await erp.get_customer_system(ticket_id=req.ticket_id)
                system = fresh["system"]
                session["host"]     = system["ip"]
                session["port"]     = system.get("port", 22)
                session["username"] = system["username"]
                session["reconnect"] = False
            except Exception:
                pass  # best-effort refresh; keep existing values

        result = await ssh.run_command(
            host=session["host"],
            port=session["port"],
            username=session["username"],
            key_path=session["key_path"],
            command=req.command,
        )

        # Mark session for reconnect if the command failed to connect
        if result.get("exit_code") in (124, 255) and not result.get("blocked"):
            session["reconnect"] = True

        audit_logger.log(
            actor="system",
            category="execution",
            action="run_command",
            command=req.command,
            result=(result.get("stdout") or "") + (result.get("stderr") or ""),
            exit_code=result.get("exit_code", 255),
        )
        return result
    except Exception as exc:
        # Never let infrastructure failures become HTTP 500 — return a valid response
        try:
            audit_logger.log(
                actor="system",
                category="execution",
                action="run_command",
                command=req.command,
                result=f"internal error: {exc}",
                exit_code=255,
            )
        except Exception:
            pass
        return {
            "blocked": False,
            "ok": False,
            "exit_code": 255,
            "stdout": "",
            "stderr": f"SSH execution failed: {str(exc)}",
            "warnings": [],
            "reason": "",
        }
    


@router.post("/validate")
async def validate(req: ValidateRequest):
    session = _sessions.get(req.ticket_id)
    if not session:
        raise HTTPException(status_code=400, detail="Session not found")
    audit_logger = audit_mod.get_logger(req.ticket_id)
    result = await ssh.run_validation(
        host=session["host"],
        port=session["port"],
        username=session["username"],
        key_path=session["key_path"],
    )
    audit_logger.log(
        actor="system",
        category="validation",
        action="run_validation",
        command="sudo /opt/hackathon/public-test.sh",
        result=result["output"],
        exit_code=0 if result["passed"] else 1,
    )
    return result


@router.post("/reset_session")
async def reset_session(req: ResetSessionRequest):
    """Clear the in-memory session for a ticket (useful for tests/dev)."""
    if req.ticket_id in _sessions:
        _sessions.pop(req.ticket_id, None)
        audit_mod.get_logger(req.ticket_id).log(
            actor="human",
            category="session",
            action="reset_session",
            command="reset_session",
            result="session cleared",
        )
        return {"reset": True}
    return {"reset": False, "reason": "session not found"}


@router.get("/audit/{ticket_id}")
async def get_audit(ticket_id: int):
    return audit_mod.get_logger(ticket_id).entries