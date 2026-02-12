from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, delete
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.application.interfaces.repositories.chat_session_repository import ChatSessionRepository
from app.domain.entities.chat_session import ChatSession
from app.infrastructure.persistence.models.chat_session_model import ChatSessionModel


class ChatSessionRepositoryImpl(ChatSessionRepository):
    """PostgreSQL implementation of chat session repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_entity(self, model: ChatSessionModel) -> ChatSession:
        """Convert database model to domain entity"""
        return ChatSession(
            id=str(model.id),
            user_id=str(model.user_id),
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    async def create(self, chat_session: ChatSession) -> ChatSession:
        """Create a new chat session"""
        model = ChatSessionModel(
            id=uuid.uuid4() if not chat_session.id else uuid.UUID(chat_session.id),
            user_id=uuid.UUID(chat_session.user_id),
            title=chat_session.title,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._to_entity(model)
    
    async def find_by_id(self, session_id: str) -> Optional[ChatSession]:
        """Find session by ID"""
        result = await self.session.execute(
            select(ChatSessionModel).where(
                ChatSessionModel.id == uuid.UUID(session_id)
            )
        )
        
        model = result.scalar_one_or_none()
        if not model:
            return None
        
        return self._to_entity(model)
    
    async def find_by_user_id(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[ChatSession]:
        """Get all sessions for a user, ordered by most recently updated"""
        result = await self.session.execute(
            select(ChatSessionModel)
            .where(ChatSessionModel.user_id == uuid.UUID(user_id))
            .order_by(desc(ChatSessionModel.updated_at))
            .limit(limit)
            .offset(offset)
        )
        
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
    
    async def update_title(self, session_id: str, title: str) -> Optional[ChatSession]:
        """Update session title"""
        result = await self.session.execute(
            update(ChatSessionModel)
            .where(ChatSessionModel.id == uuid.UUID(session_id))
            .values(
                title=title[:500],
                updated_at=datetime.now(timezone.utc)
            )
            .returning(ChatSessionModel)
        )
        
        model = result.scalar_one_or_none()
        if not model:
            return None
        
        await self.session.flush()
        return self._to_entity(model)
    
    async def delete(self, session_id: str) -> bool:
        """Delete session (messages cascade via FK)"""
        result = await self.session.execute(
            delete(ChatSessionModel).where(
                ChatSessionModel.id == uuid.UUID(session_id)
            )
        )
        
        return result.rowcount > 0