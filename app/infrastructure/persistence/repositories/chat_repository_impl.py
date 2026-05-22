from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from ....application.interfaces.repositories.chat_repository import ChatRepository
from ....domain.entities.chat_message import ChatMessage
from ..models.chat_message_model import ChatMessageModel
import uuid


class ChatRepositoryImpl(ChatRepository):
    """PostgreSQL implementation of chat repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: ChatMessageModel) -> ChatMessage:
        """Convert database model to domain entity"""
        return ChatMessage(
            id=str(model.id),
            user_id=str(model.user_id),
            session_id=str(model.session_id),
            query=model.query,
            response=model.response,
            source_document_ids=model.source_document_ids or [],
            created_at=model.created_at,
        )

    async def save(self, message: ChatMessage) -> ChatMessage:
        """Save chat message to database"""
        if not message.session_id:
            raise ValueError("session_id is required to save a chat message")

        model = ChatMessageModel(
            id=uuid.uuid4() if not message.id else uuid.UUID(message.id),
            user_id=uuid.UUID(message.user_id),
            session_id=uuid.UUID(message.session_id),
            query=message.query,
            response=message.response,
            source_document_ids=message.source_document_ids,
            created_at=message.created_at,
        )

        self.session.add(model)
        await self.session.flush()

        return self._to_entity(model)

    async def find_by_user_id(self, user_id: str, limit: int = 10) -> List[ChatMessage]:
        """Get chat history for user"""
        result = await self.session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.user_id == uuid.UUID(user_id))
            .order_by(desc(ChatMessageModel.created_at))
            .limit(limit)
        )

        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def find_by_session_id(
        self, session_id: str, limit: int = 50
    ) -> List[ChatMessage]:
        """Get all messages for a session, ordered chronologically"""
        result = await self.session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == uuid.UUID(session_id))
            .order_by(ChatMessageModel.created_at)
            .limit(limit)
        )

        models = result.scalars().all()
        return [self._to_entity(model) for model in models]
