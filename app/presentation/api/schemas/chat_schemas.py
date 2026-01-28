from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


class ChatQueryRequest(BaseModel):
    """Chat query request schema"""
    query: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What is the maintenance schedule for TX Series burners?"
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
    query: str
    response: str
    sources: List[ChatSourceResponse]
    created_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174000",
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


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    messages: List[ChatResponse]