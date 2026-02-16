from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.chat_triage import ChatTriage


class ChatTriageRepository(ABC):
    """Interface for chat triage persistence"""
    
    @abstractmethod
    async def save(self, triage: ChatTriage) -> ChatTriage:
        """Save or update a triage record"""
        pass
    
    @abstractmethod
    async def find_by_session_id(self, session_id: str) -> Optional[ChatTriage]:
        """Find triage by session ID (one triage per session)"""
        pass
    
    @abstractmethod
    async def find_by_id(self, triage_id: str) -> Optional[ChatTriage]:
        """Find triage by its own ID"""
        pass