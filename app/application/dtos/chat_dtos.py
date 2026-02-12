from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any


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