from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from .base import Base


class ChatTriageModel(Base):
    """Chat triage model — stores the pre-chat intake questionnaire answers"""
    __tablename__ = "chat_triages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('chat_sessions.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,  # One triage per session
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Q1: Burner identification
    burner_series = Column(String(20), nullable=True)  # FD, TX, DB, FDB or NULL
    burner_identified_via = Column(
        String(50), nullable=False, default="direct_selection"
    )  # direct_selection | image_identification | unknown
    
    # Q2: Serial number
    serial_number = Column(String(100), nullable=True)
    has_serial_number = Column(Boolean, default=False, nullable=False)
    
    # Q3: Issue category
    issue_category = Column(String(5), nullable=False)  # A-G
    issue_category_label = Column(String(200), nullable=True)
    issue_free_text = Column(Text, nullable=True)  # For category G
    
    # Q4: Category-specific follow-up answers (JSON)
    follow_up_answers = Column(JSON, default={})
    
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationships
    session = relationship("ChatSessionModel", back_populates="triage")
    user = relationship("UserModel")