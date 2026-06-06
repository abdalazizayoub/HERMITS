import os
import httpx

BASE_URL = os.getenv("PHOENIX_API_BASE_URL").rstrip("/")
TOKEN = os.getenv("PHOENIX_API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

_client = httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=15.0)

async def list_tickets(status="", priority=""):
    params = {}
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority

    response = await _client.get("/api/v1/me/tickets", params=params)
    response.raise_for_status()
    return response.json()

async def get_ticket(ticket_id: int):
    if ticket_id <= 0:
        raise ValueError("ticket_id must be a positive integer")
    response = await _client.get(f"/api/v1/tickets/{ticket_id}")
    response.raise_for_status()
    return response.json()

async def get_customer_system(ticket_id: int):
    if ticket_id <= 0:
        raise ValueError("ticket_id must be a positive integer")
    response = await _client.get(f"/api/v1/tickets/{ticket_id}/customer-system")
    response.raise_for_status()
    return response.json()

async def patch_ticket_status(ticket_id: int, status: str):
    if ticket_id <= 0:
        raise ValueError("ticket_id must be a positive integer")

    response = await _client.patch(f"/api/v1/tickets/{ticket_id}/status", json={"status": status})
    response.raise_for_status()
    return response.json()

async def create_activity(payload: dict):
    response = await _client.post("/api/v1/activities/create", json=payload)
    response.raise_for_status()
    return response.json()

async def reset_me():
    response = await _client.post("/api/v1/me/reset")
    response.raise_for_status()
    return response.json()