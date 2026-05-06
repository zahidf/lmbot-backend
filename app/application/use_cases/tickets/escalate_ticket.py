from datetime import datetime, timezone

from app.application.dtos.ticket_dtos import EscalateTicketDTO, TicketResponseDTO
from app.application.interfaces.repositories.ticket_repository import TicketRepository
from app.application.interfaces.repositories.ticket_activity_repository import TicketActivityRepository
from app.application.interfaces.repositories.chat_repository import ChatRepository
from app.application.interfaces.services.llm_service import LLMService
from app.domain.entities.ticket_activity import TicketActivity


class EscalateTicket:
    """
    Use Case: Escalate a ticket from lmbot to the technical team.

    Flow:
    1. Fetch and validate the ticket (ownership + open status)
    2. Fetch the chat session messages and generate an LLM summary
    3. Reassign ticket to technical_team and save
    4. Record an escalated activity entry
    """

    def __init__(
        self,
        ticket_repository: TicketRepository,
        ticket_activity_repository: TicketActivityRepository,
        chat_repository: ChatRepository,
        llm_service: LLMService,
    ):
        self.ticket_repository = ticket_repository
        self.ticket_activity_repository = ticket_activity_repository
        self.chat_repository = chat_repository
        self.llm_service = llm_service

    async def execute(self, dto: EscalateTicketDTO) -> TicketResponseDTO:
        ticket = await self.ticket_repository.find_by_id(dto.ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {dto.ticket_id} not found")

        if ticket.user_id != dto.user_id:
            raise PermissionError("You do not have permission to escalate this ticket")

        if ticket.status != "open":
            raise ValueError(f"Ticket is already {ticket.status} and cannot be escalated again")

        messages = []
        if ticket.session_id:
            chat_messages = await self.chat_repository.find_by_session_id(ticket.session_id)
            messages = [
                {"query": m.query, "response": m.response}
                for m in chat_messages
            ]

        summary = await self.llm_service.generate_summary(messages) if messages else (
            "No conversation history available."
        )

        ticket.summary = summary
        ticket.status = "escalated"
        ticket.assigned_to = "technical_team"
        ticket.updated_at = datetime.now(timezone.utc)

        updated_ticket = await self.ticket_repository.update(ticket)

        activity = TicketActivity(
            id=None,
            ticket_id=updated_ticket.id,
            action="escalated",
            actor="user",
            note=None,
            created_at=datetime.now(timezone.utc),
        )
        await self.ticket_activity_repository.save(activity)

        return TicketResponseDTO(
            ticket_id=updated_ticket.id,
            session_id=updated_ticket.session_id,
            user_id=updated_ticket.user_id,
            summary=updated_ticket.summary,
            status=updated_ticket.status,
            assigned_to=updated_ticket.assigned_to,
            created_at=updated_ticket.created_at,
            updated_at=updated_ticket.updated_at,
        )
