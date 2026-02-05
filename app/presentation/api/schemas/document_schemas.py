from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Document upload response schema"""
    id: str
    title: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    product_series: Optional[str]
    category: Optional[str]
    is_processed: bool
    chunk_count: int
    created_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "TX Series Manual",
                "file_name": "tx_manual.pdf",
                "file_path": "/uploads/123e4567.pdf",
                "file_type": "pdf",
                "file_size": 1024000,
                "product_series": "TX",
                "category": "Manual",
                "is_processed": False,
                "chunk_count": 0,
                "created_at": "2026-01-28T09:33:09Z"
            }
        }
    )


class DocumentListItem(BaseModel):
    """Document list item schema"""
    id: str
    title: str
    file_name: str
    file_type: str
    file_size: int
    product_series: Optional[str]
    category: Optional[str]
    is_processed: bool
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Document list response schema"""
    documents: List[DocumentListItem]
    total: int


class DocumentDeleteResponse(BaseModel):
    """Document delete response schema"""
    message: str
    id: str