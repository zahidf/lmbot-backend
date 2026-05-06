from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class EscalateTicketDTO:
    ticket_id: str
    user_id: str


@dataclass
class TicketActivityDTO:
    id: str
    action: str
    actor: str
    note: Optional[str]
    created_at: datetime


@dataclass
class TicketResponseDTO:
    ticket_id: str
    session_id: Optional[str]
    user_id: str
    summary: Optional[str]
    status: str
    assigned_to: str
    created_at: datetime
    updated_at: datetime


@dataclass
class TicketDetailDTO:
    ticket_id: str
    session_id: Optional[str]
    user_id: str
    summary: Optional[str]
    status: str
    assigned_to: str
    activities: List[TicketActivityDTO] = field(default_factory=list)
    created_at: datetime = None
    updated_at: datetime = None
