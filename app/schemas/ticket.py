from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Priority = Literal["low", "medium", "high", "urgent"]
TicketStatus = Literal["open", "pending_approval", "resolved", "escalated"]


class Ticket(BaseModel):
    id: str
    customer_id: str | None
    intent: str
    priority: Priority
    status: TicketStatus
    summary: str
    assigned_team: str
    notes: list[str]
    created_at: datetime
    updated_at: datetime

