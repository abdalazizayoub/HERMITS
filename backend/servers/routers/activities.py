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


@router.post("/submit")
async def submit_activity(payload: ActivityPayload):
    try:
        await erp.create_activity(payload.dict())
        await erp.patch_ticket_status(payload.ticket_id, "DONE")
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