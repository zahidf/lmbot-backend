from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.application.interfaces.repositories.chat_triage_repository import (
    ChatTriageRepository,
)
from app.domain.entities.chat_triage import ChatTriage
from app.infrastructure.persistence.models.chat_triage_model import ChatTriageModel


class ChatTriageRepositoryImpl(ChatTriageRepository):
    """PostgreSQL implementation of chat triage repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: ChatTriageModel) -> ChatTriage:
        """Convert database model to domain entity"""
        return ChatTriage(
            id=str(model.id),
            session_id=str(model.session_id),
            user_id=str(model.user_id),
            burner_series=model.burner_series,
            burner_identified_via=model.burner_identified_via,
            serial_number=model.serial_number,
            has_serial_number=model.has_serial_number,
            issue_category=model.issue_category,
            issue_category_label=model.issue_category_label,
            issue_free_text=model.issue_free_text,
            follow_up_answers=model.follow_up_answers or {},
            created_at=model.created_at,
        )

    async def save(self, triage: ChatTriage) -> ChatTriage:
        """Save or update a triage record"""
        model = ChatTriageModel(
            id=uuid.UUID(triage.id) if triage.id else uuid.uuid4(),
            session_id=uuid.UUID(triage.session_id),
            user_id=uuid.UUID(triage.user_id),
            burner_series=triage.burner_series,
            burner_identified_via=triage.burner_identified_via,
            serial_number=triage.serial_number,
            has_serial_number=triage.has_serial_number,
            issue_category=triage.issue_category,
            issue_category_label=triage.issue_category_label,
            issue_free_text=triage.issue_free_text,
            follow_up_answers=triage.follow_up_answers,
            created_at=triage.created_at,
        )

        model = await self.session.merge(model)
        await self.session.flush()

        return self._to_entity(model)

    async def find_by_session_id(self, session_id: str) -> Optional[ChatTriage]:
        """Find triage by session ID"""
        result = await self.session.execute(
            select(ChatTriageModel).where(
                ChatTriageModel.session_id == uuid.UUID(session_id)
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_id(self, triage_id: str) -> Optional[ChatTriage]:
        """Find triage by ID"""
        result = await self.session.execute(
            select(ChatTriageModel).where(ChatTriageModel.id == uuid.UUID(triage_id))
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
