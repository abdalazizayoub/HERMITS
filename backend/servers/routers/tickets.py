from fastapi import APIRouter, HTTPException
from erp import client as erp
import httpx

router = APIRouter()

@router.get("/")
async def list_tickets(status: str = "", priority: str = ""):
    try:
        tickets = await erp.list_tickets(status=status, priority=priority)
        return {"tickets": tickets}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    
@router.get("/{ticket_id}")
async def get_ticket(ticket_id: int):
    try:
        ticket = await erp.get_ticket(ticket_id=ticket_id)
        system = await erp.get_customer_system(ticket_id=ticket_id)
        return {"ticket": ticket, "system": system}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        else:
            raise HTTPException(status_code=502, detail=str(e))
        
@router.patch("/{ticket_id}/status")
async def set_status(ticket_id: int, body: dict):
    if "status" not in body:
        raise HTTPException(status_code=400, detail="Missing 'status' in request body")
    try:
        updated_ticket = await erp.patch_ticket_status(ticket_id=ticket_id, status=body["status"])
        return {"ticket": updated_ticket}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        else:
            raise HTTPException(status_code=502, detail=str(e))
