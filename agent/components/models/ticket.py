from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Ticket(BaseModel):
    id: int
    title: str
    description: str
    priority: str
    status: str
    customer_id: int
    customer_name: str
    tags: list[str] = []
    sla_due_at: Optional[datetime] = None
    created_at: datetime
    service_hint: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_port: int = 22

    def is_high_priority(self) -> bool:
        return self.priority.lower() in ("high", "critical")

    def is_open(self) -> bool:
        return self.status.upper() == "OPEN"
