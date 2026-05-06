from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime


class ChatQueryRequest(BaseModel):
    """Chat query request schema"""
    query: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None  # None = create new chat session
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What is the maintenance schedule for TX Series burners?",
                "session_id": None
            }
        }
    )


class ChatSourceResponse(BaseModel):
    """Source document used for response"""
    document_id: str
    content: str
    similarity_score: float
    metadata: dict


class ChatResponse(BaseModel):
    """Chat response schema"""
    message_id: Optional[str]
    session_id: str
    query: str
    response: str
    sources: List[ChatSourceResponse]
    created_at: datetime
    can_escalate: bool = False
    ticket_id: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "789e0123-e89b-12d3-a456-426614174000",
                "query": "What is the maintenance schedule?",
                "response": "The TX Series maintenance schedule includes...",
                "sources": [
                    {
                        "document_id": "doc-123",
                        "content": "Monthly maintenance includes...",
                        "similarity_score": 0.95,
                        "metadata": {"product_series": "TX"}
                    }
                ],
                "created_at": "2026-01-28T09:33:09Z"
            }
        }
    )


class ChatSessionResponse(BaseModel):
    """Chat session schema"""
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(BaseModel):
    """Chat session with messages"""
    id: str
    title: Optional[str]
    messages: List[ChatResponse]
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    """List of chat sessions"""
    sessions: List[ChatSessionResponse]
    total: int


class ChatSessionUpdateRequest(BaseModel):
    """Request to update session title"""
    title: str


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    messages: List[ChatResponse]