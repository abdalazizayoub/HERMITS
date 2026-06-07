"""
Shared helpers for the agent API layer.
The ERP client import is deferred so this module is importable before sys.path
is fully configured (e.g., during unit tests).
"""
from __future__ import annotations


async def fetch_ticket_from_erp(ticket_id: int):
    """
    Fetches ticket data + customer-system SSH details from the Phoenix ERP,
    then assembles and returns a components.models.ticket.Ticket instance.
    """
    from erp import client as erp  # backend/ must be on sys.path
    from components.models.ticket import Ticket  # agent/ must be on sys.path

    ticket_data: dict = await erp.get_ticket(ticket_id)

    try:
        system_data: dict = await erp.get_customer_system(ticket_id)
        system = system_data.get("system", {})
    except Exception:
        system = {}

    return Ticket(
        **ticket_data,
        ssh_host=system.get("ip"),
        ssh_user=system.get("username"),
        ssh_port=system.get("port", 22),
    )
