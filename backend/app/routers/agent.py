from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.erp import client as erp
from app.ssh import runner as ssh
from app.audit import logger as audit_mod

router = APIRouter()

_sessions: dict[int, dict] = {}


class ReconRequest(BaseModel):
    ticket_id: int

class ExecuteRequest(BaseModel):
    ticket_id: int
    command:   str
    category:  str

class ValidateRequest(BaseModel):
    ticket_id: int


@router.post("/recon")
async def run_recon(req: ReconRequest):
    try:
        ticket = await erp.get_ticket(ticket_id=req.ticket_id)
        system = await erp.get_customer_system(ticket_id=req.ticket_id)
        system = system['system']
        host = system['ip']
        port = system.get('port', 22)
        username = system['username']
        key_path = ssh.get_key_path(req.ticket_id)
        recon_results = await ssh.run_recon(host, port, username, key_path)
        _sessions[req.ticket_id] = {
            "host": host,
            "port": port,
            "username": username,
            "key_path": key_path,
            "recon": recon_results,
        }
        audit_logger = audit_mod.get_logger(req.ticket_id)
        audit_logger.log(
            actor="system",
            category="recon",
            action="run_recon",
            command=f"ssh recon on {host}:{port} as {username}",
            result=f"recon complete, {len(recon_results)} keys collected",
        )
        return {"recon": recon_results}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/execute")
async def execute_command(req: ExecuteRequest):
    session = _sessions.get(req.ticket_id)
    if not session:
        raise HTTPException(status_code=400, detail="Session not found")
    audit_logger = audit_mod.get_logger(req.ticket_id)
    audit_logger.log(
        actor="human",
        category="approval",
        action="approve_command",
        command=req.command,
    )
    result = await ssh.run_command(
        host=session["host"],
        port=session["port"],
        username=session["username"],
        key_path=session["key_path"],
        command=req.command,
    )
    audit_logger.log(
        actor="system",
        category="execution",
        action="run_command",
        command=req.command,
        result=result["stdout"] + result["stderr"],
        exit_code=result["exit_code"],
    )
    return result
    


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


@router.get("/audit/{ticket_id}")
async def get_audit(ticket_id: int):
    return audit_mod.get_logger(ticket_id).entries