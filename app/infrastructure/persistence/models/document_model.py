from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from .base import Base


class DocumentModel(Base):
    """Document metadata model"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, etc.
    file_path = Column(String(500), nullable=False)
    
    # Product association
    product_series = Column(String(50), nullable=True, index=True)  # TX, FD, HC, KS
    category = Column(String(100), nullable=True)  # e.g Manual
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    chunk_count = Column(Integer, default=0)
    
    # Timestamps
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
