from sqlalchemy import Column, String, DateTime, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from .base import Base


class ChatMessageModel(Base):
    """Chat message model"""
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    
    # Source documents used for response
    source_document_ids = Column(ARRAY(String), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
