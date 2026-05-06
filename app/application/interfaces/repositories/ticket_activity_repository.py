from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.ticket_activity import TicketActivity


class TicketActivityRepository(ABC):

    @abstractmethod
    async def save(self, activity: TicketActivity) -> TicketActivity:
        pass

    @abstractmethod
    async def find_by_ticket_id(self, ticket_id: str) -> List[TicketActivity]:
        pass
