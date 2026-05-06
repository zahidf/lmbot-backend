from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.chat_message import ChatMessage


class ChatRepository(ABC):
    """Interface for chat message persistence"""
    
    @abstractmethod
    async def save(self, message: ChatMessage) -> ChatMessage:
        """Save chat message"""
        pass
    
    @abstractmethod
    async def find_by_user_id(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ChatMessage]:
        """Get chat history for user"""
        pass

    @abstractmethod
    async def find_by_session_id(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get all messages for a session in chronological order"""
        pass