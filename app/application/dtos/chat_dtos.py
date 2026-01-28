from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class ChatQueryDTO:
    """Input DTO for chat query"""
    user_id: str
    query: str


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
    query: str
    response: str
    sources: List[Dict[str, Any]]
    created_at: datetime