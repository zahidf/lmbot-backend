from dataclasses import dataclass
from datetime import datetime
from typing import Optional


ACTIONS = {
    "created": "Ticket created",
    "escalated": "Escalated to technical team",
    "resolved": "Resolved",
}


@dataclass
class TicketActivity:
    id: Optional[str]
    ticket_id: str
    action: str           # "created" | "escalated" | "resolved"
    actor: str            # "lmbot" | "user"
    note: Optional[str]
    created_at: datetime
