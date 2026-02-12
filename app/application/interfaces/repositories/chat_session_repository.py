from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.chat_session import ChatSession


class ChatSessionRepository(ABC):
    """Interface for chat session persistence"""
    
    @abstractmethod
    async def create(self, session: ChatSession) -> ChatSession:
        """Create a new chat session"""
        pass
    
    @abstractmethod
    async def find_by_id(self, session_id: str) -> Optional[ChatSession]:
        """Find session by ID"""
        pass
    
    @abstractmethod
    async def find_by_user_id(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[ChatSession]:
        """Get all sessions for a user, ordered by most recent"""
        pass
    
    @abstractmethod
    async def update_title(self, session_id: str, title: str) -> Optional[ChatSession]:
        """Update session title"""
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete session and all its messages (cascade)"""
        pass