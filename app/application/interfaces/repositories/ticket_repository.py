from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.ticket import Ticket


class TicketRepository(ABC):

    @abstractmethod
    async def save(self, ticket: Ticket) -> Ticket:
        pass

    @abstractmethod
    async def find_by_id(self, ticket_id: str) -> Optional[Ticket]:
        pass

    @abstractmethod
    async def find_by_session_id(self, session_id: str) -> Optional[Ticket]:
        pass

    @abstractmethod
    async def find_by_user_id(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> List[Ticket]:
        pass

    @abstractmethod
    async def update(self, ticket: Ticket) -> Ticket:
        pass
