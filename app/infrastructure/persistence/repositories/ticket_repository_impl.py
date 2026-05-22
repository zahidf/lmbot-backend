from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.application.interfaces.repositories.ticket_repository import TicketRepository
from app.domain.entities.ticket import Ticket
from app.infrastructure.persistence.models.ticket_model import TicketModel


class TicketRepositoryImpl(TicketRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: TicketModel) -> Ticket:
        return Ticket(
            id=str(model.id),
            session_id=str(model.session_id) if model.session_id else None,
            user_id=str(model.user_id),
            summary=model.summary,
            status=model.status,
            assigned_to=model.assigned_to,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def save(self, ticket: Ticket) -> Ticket:
        model = TicketModel(
            id=uuid.uuid4() if not ticket.id else uuid.UUID(ticket.id),
            session_id=uuid.UUID(ticket.session_id) if ticket.session_id else None,
            user_id=uuid.UUID(ticket.user_id),
            summary=ticket.summary,
            status=ticket.status,
            assigned_to=ticket.assigned_to,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        result = await self.session.execute(
            select(TicketModel).where(TicketModel.id == uuid.UUID(ticket_id))
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_session_id(self, session_id: str) -> Optional[Ticket]:
        result = await self.session.execute(
            select(TicketModel).where(TicketModel.session_id == uuid.UUID(session_id))
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_user_id(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> List[Ticket]:
        result = await self.session.execute(
            select(TicketModel)
            .where(TicketModel.user_id == uuid.UUID(user_id))
            .order_by(desc(TicketModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, ticket: Ticket) -> Ticket:
        result = await self.session.execute(
            update(TicketModel)
            .where(TicketModel.id == uuid.UUID(ticket.id))
            .values(
                summary=ticket.summary,
                status=ticket.status,
                assigned_to=ticket.assigned_to,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(TicketModel)
        )
        model = result.scalar_one()
        await self.session.flush()
        return self._to_entity(model)
