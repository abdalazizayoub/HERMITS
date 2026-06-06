from datetime import datetime
from pydantic import BaseModel


class Activity(BaseModel):
    ticket_id: int
    start_datetime: datetime
    end_datetime: datetime
    summary: str
    root_cause: str
    actions_taken: str
    commands_summary: str
    validation_result: str
