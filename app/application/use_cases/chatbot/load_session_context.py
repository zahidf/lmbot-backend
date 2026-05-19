from app.application.interfaces.repositories.chat_session_repository import ChatSessionRepository
from app.application.interfaces.repositories.chat_repository import ChatRepository
from app.application.interfaces.repositories.chat_triage_repository import ChatTriageRepository
from app.application.interfaces.repositories.ticket_repository import TicketRepository
from app.application.interfaces.repositories.ticket_activity_repository import TicketActivityRepository
from app.application.interfaces.repositories.vector_store_repository import VectorStoreRepository
from app.application.dtos.chat_dtos import SessionContextDTO, ChatResponseDTO
from app.application.dtos.triage_dtos import TriageResponseDTO
from app.application.dtos.ticket_dtos import TicketDetailDTO, TicketActivityDTO
from app.domain.entities.chat_triage import ChatTriage


class LoadSessionContext:
    """
    Session load
    """

    def __init__(
        self,
        session_repository: ChatSessionRepository,
        chat_repository: ChatRepository,
        triage_repository: ChatTriageRepository,
        ticket_repository: TicketRepository,
        ticket_activity_repository: TicketActivityRepository,
        vector_store_repository: VectorStoreRepository,
    ):
        self._sessions = session_repository
        self._messages = chat_repository
        self._triages = triage_repository
        self._tickets = ticket_repository
        self._activities = ticket_activity_repository
        self._vectors = vector_store_repository

    async def execute(self, session_id: str, user_id: str) -> SessionContextDTO:
        session = await self._sessions.find_by_id(session_id)

        if not session:
            raise ValueError("Session not found")
        if session.user_id != user_id:
            raise PermissionError("Access denied")

        messages = await self._messages.find_by_session_id(session_id)
        triage = await self._triages.find_by_session_id(session_id)
        ticket = await self._tickets.find_by_session_id(session_id)

        activities = []
        if ticket:
            activities = await self._activities.find_by_ticket_id(ticket.id)

        all_chunk_ids = [cid for msg in messages for cid in (msg.source_document_ids or [])]
        chunks_by_id = {}
        if all_chunk_ids:
            chunks = await self._vectors.get_chunks_by_ids(all_chunk_ids)
            chunks_by_id = {c["id"]: c for c in chunks}

        message_dtos = [
            ChatResponseDTO(
                message_id=msg.id,
                session_id=msg.session_id,
                query=msg.query,
                response=msg.response,
                sources=[
                    {
                        "document_id": chunks_by_id[cid]["document_id"],
                        "content": chunks_by_id[cid]["content"],
                        "similarity_score": 0.0,
                        "metadata": chunks_by_id[cid]["metadata"],
                    }
                    for cid in (msg.source_document_ids or [])
                    if cid in chunks_by_id
                ],
                created_at=msg.created_at,
            )
            for msg in messages
        ]

        triage_dto = None
        triage_config = None
        if triage:
            triage_dto = TriageResponseDTO(
                triage_id=triage.id,
                session_id=triage.session_id,
                burner_series=triage.burner_series,
                serial_number=triage.serial_number,
                issue_category=triage.issue_category,
                issue_category_label=triage.issue_category_label or "",
                context_summary=triage.get_context_summary(),
                created_at=triage.created_at,
            )
            triage_config = {
                "burner_series": ChatTriage.BURNER_SERIES,
                "issue_categories": ChatTriage.ISSUE_CATEGORIES,
                "serial_number_example": "J123456",
                "serial_number_tooltip": (
                    "Usually found on the burner rating plate "
                    "or inside the gas valve control panel."
                ),
            }

        ticket_dto = None
        if ticket:
            ticket_dto = TicketDetailDTO(
                ticket_id=ticket.id,
                session_id=ticket.session_id,
                user_id=ticket.user_id,
                summary=ticket.summary,
                status=ticket.status,
                assigned_to=ticket.assigned_to,
                activities=[
                    TicketActivityDTO(
                        id=a.id,
                        action=a.action,
                        actor=a.actor,
                        note=a.note,
                        created_at=a.created_at,
                    )
                    for a in activities
                ],
                created_at=ticket.created_at,
                updated_at=ticket.updated_at,
            )

        return SessionContextDTO(
            session_id=str(session.id),
            session_title=session.title,
            session_created_at=session.created_at,
            session_updated_at=session.updated_at,
            messages=message_dtos,
            triage=triage_dto,
            triage_config=triage_config,
            ticket=ticket_dto,
        )
