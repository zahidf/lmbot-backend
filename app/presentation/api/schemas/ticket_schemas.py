from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TicketActivityResponse(BaseModel):
    id: str
    action: str
    actor: str
    note: Optional[str]
    created_at: datetime


class TicketResponse(BaseModel):
    ticket_id: str
    session_id: Optional[str]
    summary: Optional[str]
    status: str
    assigned_to: str
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(BaseModel):
    ticket_id: str
    session_id: Optional[str]
    summary: Optional[str]
    status: str
    assigned_to: str
    activities: List[TicketActivityResponse]
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    tickets: List[TicketResponse]
    total: int
