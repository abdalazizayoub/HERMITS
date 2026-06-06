import pytest
import httpx
import respx
from servers.erp.client import list_tickets, get_ticket, get_customer_system, patch_ticket_status

BASE = "http://68.210.101.85:8000"

MOCK_TICKET = {
    "id": 7001,
    "title": "Status API intermittently unavailable",
    "priority": "high",
    "status": "OPEN",
    "customer_id": 5001,
    "customer_name": "Nordlicht Logistik GmbH",
    "tags": [],
    "sla_due_at": None,
    "created_at": "2026-06-05T13:54:33.697508",
    "description": "test"
}

MOCK_SYSTEM = {
    "ticket_id": 7001,
    "customer_id": 5001,
    "system": {
        "ip": "51.124.197.57",
        "port": 22,
        "username": "azureuser",
        "os": "Ubuntu 22.04 LTS",
        "notes": "test vm"
    }
}


@pytest.mark.asyncio
@respx.mock
async def test_list_tickets():
    respx.get(f"{BASE}/api/v1/me/tickets").mock(
        return_value=httpx.Response(200, json=[MOCK_TICKET])
    )
    result = await list_tickets()
    assert len(result) == 1
    assert result[0]["id"] == 7001


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket():
    respx.get(f"{BASE}/api/v1/tickets/7001").mock(
        return_value=httpx.Response(200, json=MOCK_TICKET)
    )
    result = await get_ticket(7001)
    assert result["id"] == 7001
    assert result["status"] == "OPEN"


@pytest.mark.asyncio
@respx.mock
async def test_get_customer_system():
    respx.get(f"{BASE}/api/v1/tickets/7001/customer-system").mock(
        return_value=httpx.Response(200, json=MOCK_SYSTEM)
    )
    result = await get_customer_system(7001)
    assert result["system"]["ip"] == "51.124.197.57"


@pytest.mark.asyncio
@respx.mock
async def test_patch_ticket_status():
    respx.patch(f"{BASE}/api/v1/tickets/7001/status").mock(
        return_value=httpx.Response(200, json={**MOCK_TICKET, "status": "DONE"})
    )
    result = await patch_ticket_status(7001, "DONE")
    assert result["status"] == "DONE"


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_404():
    respx.get(f"{BASE}/api/v1/tickets/9999").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(httpx.HTTPStatusError):
        await get_ticket(9999)