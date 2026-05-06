import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock
from app.application.use_cases.tickets.escalate_ticket import EscalateTicket
from app.application.dtos.ticket_dtos import EscalateTicketDTO, TicketResponseDTO
from app.domain.entities.ticket import Ticket
from app.domain.entities.chat_message import ChatMessage


def _make_ticket(**kwargs) -> Ticket:
    defaults = dict(
        id="ticket-123",
        session_id="session-123",
        user_id="user-123",
        summary=None,
        status="open",
        assigned_to="lmbot",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return Ticket(**defaults)


class TestEscalateTicket:

    @pytest.fixture
    def mock_ticket_repository(self):
        repo = AsyncMock()
        ticket = _make_ticket()
        repo.find_by_id.return_value = ticket

        async def update_mock(t):
            return t

        repo.update.side_effect = update_mock
        return repo

    @pytest.fixture
    def mock_ticket_activity_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_chat_repository(self):
        repo = AsyncMock()
        repo.find_by_session_id.return_value = [
            ChatMessage(
                id="msg-1",
                user_id="user-123",
                session_id="session-123",
                query="My burner won't start",
                response="I don't have enough information to help.",
                source_document_ids=[],
                created_at=datetime.now(UTC),
            )
        ]
        return repo

    @pytest.fixture
    def mock_llm_service(self):
        service = AsyncMock()
        service.generate_summary.return_value = (
            "Customer reported a TX series burner fault. "
            "The bot was unable to resolve the issue."
        )
        return service

    @pytest.fixture
    def use_case(self, mock_ticket_repository, mock_ticket_activity_repository, mock_chat_repository, mock_llm_service):
        return EscalateTicket(
            ticket_repository=mock_ticket_repository,
            ticket_activity_repository=mock_ticket_activity_repository,
            chat_repository=mock_chat_repository,
            llm_service=mock_llm_service,
        )

    @pytest.fixture
    def valid_dto(self):
        return EscalateTicketDTO(ticket_id="ticket-123", user_id="user-123")

    # ─── Happy path ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_returns_ticket_response_dto(self, use_case, valid_dto):
        result = await use_case.execute(valid_dto)
        assert isinstance(result, TicketResponseDTO)

    @pytest.mark.asyncio
    async def test_ticket_reassigned_to_technical_team(self, use_case, valid_dto, mock_ticket_repository):
        result = await use_case.execute(valid_dto)
        assert result.status == "escalated"
        assert result.assigned_to == "technical_team"

    @pytest.mark.asyncio
    async def test_summary_populated_from_llm(self, use_case, valid_dto, mock_llm_service):
        result = await use_case.execute(valid_dto)
        assert result.summary == mock_llm_service.generate_summary.return_value

    @pytest.mark.asyncio
    async def test_llm_called_with_message_pairs(
        self, use_case, valid_dto, mock_llm_service, mock_chat_repository
    ):
        await use_case.execute(valid_dto)
        call_args = mock_llm_service.generate_summary.call_args[0][0]
        assert isinstance(call_args, list)
        assert call_args[0]["query"] == "My burner won't start"
        assert call_args[0]["response"] == "I don't have enough information to help."

    @pytest.mark.asyncio
    async def test_activity_saved_with_escalated_action(
        self, use_case, valid_dto, mock_ticket_activity_repository
    ):
        await use_case.execute(valid_dto)
        mock_ticket_activity_repository.save.assert_called_once()
        saved_activity = mock_ticket_activity_repository.save.call_args[0][0]
        assert saved_activity.action == "escalated"
        assert saved_activity.actor == "user"
        assert saved_activity.ticket_id == "ticket-123"

    @pytest.mark.asyncio
    async def test_ticket_updated_in_repository(self, use_case, valid_dto, mock_ticket_repository):
        await use_case.execute(valid_dto)
        mock_ticket_repository.update.assert_called_once()
        updated = mock_ticket_repository.update.call_args[0][0]
        assert updated.status == "escalated"
        assert updated.assigned_to == "technical_team"

    # ─── No session history ───────────────────────────────────

    @pytest.mark.asyncio
    async def test_fallback_summary_when_no_session(
        self, use_case, valid_dto, mock_ticket_repository, mock_llm_service
    ):
        """Ticket with no session_id gets a fallback summary without calling the LLM"""
        mock_ticket_repository.find_by_id.return_value = _make_ticket(session_id=None)

        result = await use_case.execute(valid_dto)

        mock_llm_service.generate_summary.assert_not_called()
        assert result.summary == "No conversation history available."

    @pytest.mark.asyncio
    async def test_fallback_summary_when_no_messages(
        self, use_case, valid_dto, mock_chat_repository, mock_llm_service
    ):
        """Session exists but has no messages — fallback summary, no LLM call"""
        mock_chat_repository.find_by_session_id.return_value = []

        result = await use_case.execute(valid_dto)

        mock_llm_service.generate_summary.assert_not_called()
        assert result.summary == "No conversation history available."

    # ─── Error cases ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_raises_value_error_when_ticket_not_found(self, use_case, mock_ticket_repository):
        mock_ticket_repository.find_by_id.return_value = None
        dto = EscalateTicketDTO(ticket_id="ghost-ticket", user_id="user-123")

        with pytest.raises(ValueError, match="not found"):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_raises_permission_error_for_wrong_user(self, use_case, mock_ticket_repository):
        mock_ticket_repository.find_by_id.return_value = _make_ticket(user_id="other-user")
        dto = EscalateTicketDTO(ticket_id="ticket-123", user_id="user-123")

        with pytest.raises(PermissionError):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_raises_value_error_when_already_escalated(self, use_case, mock_ticket_repository):
        mock_ticket_repository.find_by_id.return_value = _make_ticket(
            status="escalated", assigned_to="technical_team"
        )
        dto = EscalateTicketDTO(ticket_id="ticket-123", user_id="user-123")

        with pytest.raises(ValueError, match="already escalated"):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_raises_value_error_when_resolved(self, use_case, mock_ticket_repository):
        mock_ticket_repository.find_by_id.return_value = _make_ticket(status="resolved")
        dto = EscalateTicketDTO(ticket_id="ticket-123", user_id="user-123")

        with pytest.raises(ValueError):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_no_update_when_validation_fails(
        self, use_case, mock_ticket_repository, valid_dto
    ):
        """Repository update is never called when ownership check fails"""
        mock_ticket_repository.find_by_id.return_value = _make_ticket(user_id="other-user")

        with pytest.raises(PermissionError):
            await use_case.execute(valid_dto)

        mock_ticket_repository.update.assert_not_called()
