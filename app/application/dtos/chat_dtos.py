from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from .triage_dtos import TriageResponseDTO
from .ticket_dtos import TicketDetailDTO


@dataclass
class ChatQueryDTO:
    """Input DTO for chat query"""
    user_id: str
    query: str
    session_id: Optional[str] = None  # None = create new session


@dataclass
class ChatSourceDTO:
    """Source document in response"""
    document_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]


@dataclass
class ChatResponseDTO:
    """Output DTO for chat response"""
    message_id: Optional[str]
    session_id: str
    query: str
    response: str
    sources: List[Dict[str, Any]]
    created_at: datetime
    can_escalate: bool = False
    ticket_id: Optional[str] = None


@dataclass
class ChatSessionDTO:
    """Output DTO for chat session"""
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class ChatSessionDetailDTO:
    """Output DTO for chat session with messages"""
    id: str
    user_id: str
    title: Optional[str]
    messages: List[ChatResponseDTO]
    created_at: datetime
    updated_at: datetime


@dataclass
class SessionContextDTO:
    """Output DTO for session load."""
    session_id: str
    session_title: Optional[str]
    session_created_at: datetime
    session_updated_at: datetime
    messages: List[ChatResponseDTO]
    triage: Optional[TriageResponseDTO]
    triage_config: Optional[Dict[str, Any]]
    ticket: Optional[TicketDetailDTO]