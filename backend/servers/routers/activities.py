from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from erp import client as erp
from audit import logger as audit_mod

router = APIRouter()


class ActivityPayload(BaseModel):
    ticket_id:         int
    start_datetime:    str
    end_datetime:      str
    summary:           str
    root_cause:        str
    actions_taken:     str
    commands_summary:  str
    validation_result: str


@router.post("/reset")
async def reset_environment():
    """Reset all VMs and ERP activities to initial state."""
    try:
        result = await erp.reset_me()
        from routers.tickets import _pipeline_cache, _pipeline_running
        _pipeline_cache.clear()
        _pipeline_running.clear()
        return {"ok": True, "detail": result}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/submit")
async def submit_activity(payload: ActivityPayload):
    try:
        await erp.create_activity(payload.dict())
        # Do NOT auto-mark DONE here — the frontend ActionBar does it explicitly
        # only after the technician reviews validation and confirms completion.
        audit_logger = audit_mod.get_logger(payload.ticket_id)
        audit_logger.log(
            actor="system",
            category="activity_submission",
            action="submit_activity",
            command=f"submit activity for ticket {payload.ticket_id}",
            result=f"summary: {payload.summary}",
        )
        audit_mod.close_session(payload.ticket_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))