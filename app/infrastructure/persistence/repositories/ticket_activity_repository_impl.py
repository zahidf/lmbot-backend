from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.application.interfaces.repositories.ticket_activity_repository import (
    TicketActivityRepository,
)
from app.domain.entities.ticket_activity import TicketActivity
from app.infrastructure.persistence.models.ticket_activity_model import (
    TicketActivityModel,
)


class TicketActivityRepositoryImpl(TicketActivityRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: TicketActivityModel) -> TicketActivity:
        return TicketActivity(
            id=str(model.id),
            ticket_id=str(model.ticket_id),
            action=model.action,
            actor=model.actor,
            note=model.note,
            created_at=model.created_at,
        )

    async def save(self, activity: TicketActivity) -> TicketActivity:
        model = TicketActivityModel(
            id=uuid.uuid4() if not activity.id else uuid.UUID(activity.id),
            ticket_id=uuid.UUID(activity.ticket_id),
            action=activity.action,
            actor=activity.actor,
            note=activity.note,
            created_at=activity.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def find_by_ticket_id(self, ticket_id: str) -> List[TicketActivity]:
        result = await self.session.execute(
            select(TicketActivityModel)
            .where(TicketActivityModel.ticket_id == uuid.UUID(ticket_id))
            .order_by(TicketActivityModel.created_at)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
