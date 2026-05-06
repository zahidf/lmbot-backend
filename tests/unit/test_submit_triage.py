import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock
from app.application.use_cases.chatbot.submit_triage import SubmitTriage
from app.application.dtos.triage_dtos import TriageSubmissionDTO, TriageResponseDTO
from app.domain.entities.chat_triage import ChatTriage
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.ticket import Ticket


class TestSubmitTriage:

    # Fixtures
    @pytest.fixture
    def mock_triage_repository(self):
        repo = AsyncMock()
        repo.find_by_session_id.return_value = None

        async def save_mock(triage):
            triage.id = "triage-saved-001"
            triage.created_at = datetime.now(UTC)
            return triage

        repo.save.side_effect = save_mock
        return repo

    @pytest.fixture
    def mock_session_repository(self):
        repo = AsyncMock()
        now = datetime.now(UTC)
        repo.find_by_id.return_value = ChatSession(
            id="session-existing-001",
            user_id="user-123",
            title="TX Series — Burner Will Not Start",
            created_at=now,
            updated_at=now,
        )

        async def create_mock(session):
            session.id = "session-new-001"
            return session

        repo.create.side_effect = create_mock
        return repo

    @pytest.fixture
    def mock_ticket_repository(self):
        repo = AsyncMock()
        ticket = Ticket(
            id="ticket-001",
            session_id="session-new-001",
            user_id="user-123",
            summary=None,
            status="open",
            assigned_to="lmbot",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        repo.save.return_value = ticket
        return repo

    @pytest.fixture
    def mock_ticket_activity_repository(self):
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_triage_repository, mock_session_repository, mock_ticket_repository, mock_ticket_activity_repository):
        return SubmitTriage(
            triage_repository=mock_triage_repository,
            session_repository=mock_session_repository,
            ticket_repository=mock_ticket_repository,
            ticket_activity_repository=mock_ticket_activity_repository,
        )

    @pytest.fixture
    def valid_dto(self):
        return TriageSubmissionDTO(
            user_id="user-123",
            session_id=None,
            burner_series="TX",
            burner_identified_via="direct_selection",
            serial_number="J123456",
            has_serial_number=True,
            issue_category="A",
            issue_free_text=None,
            follow_up_answers={},
        )

    # Happy Paths

    @pytest.mark.asyncio
    async def test_creates_new_session_when_no_session_id(self, use_case, valid_dto, mock_session_repository, mock_triage_repository):
        result = await use_case.execute(valid_dto)
        assert result.session_id == "session-new-001"
        assert result.triage_id == "triage-saved-001"
        mock_session_repository.create.assert_called_once()
        mock_session_repository.find_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_attaches_to_existing_session(self, use_case, valid_dto, mock_session_repository, mock_triage_repository):
        valid_dto.session_id = "session-existing-001"
        result = await use_case.execute(valid_dto)
        assert result.session_id == "session-existing-001"
        mock_session_repository.find_by_id.assert_called_once_with("session-existing-001")
        mock_session_repository.create.assert_not_called()
        mock_triage_repository.find_by_session_id.assert_called_once_with("session-existing-001")

    @pytest.mark.asyncio
    async def test_returns_triage_response_dto(self, use_case, valid_dto):
        result = await use_case.execute(valid_dto)
        assert isinstance(result, TriageResponseDTO)

    @pytest.mark.asyncio
    async def test_session_title_known_burner(self, use_case, valid_dto, mock_session_repository):
        await use_case.execute(valid_dto)
        created_session = mock_session_repository.create.call_args[0][0]
        assert created_session.title == "TX Series — Burner Will Not Start"

    @pytest.mark.asyncio
    async def test_session_title_unknown_burner(self, use_case, valid_dto, mock_session_repository):
        valid_dto.burner_series = None
        await use_case.execute(valid_dto)
        created_session = mock_session_repository.create.call_args[0][0]
        assert created_session.title == "Unknown Burner — Burner Will Not Start"

    @pytest.mark.asyncio
    async def test_saves_triage_with_correct_fields(self, use_case, valid_dto, mock_triage_repository):
        await use_case.execute(valid_dto)
        saved_triage = mock_triage_repository.save.call_args[0][0]
        assert saved_triage.session_id == "session-new-001"
        assert saved_triage.user_id == "user-123"
        assert saved_triage.burner_series == "TX"
        assert saved_triage.issue_category == "A"
        assert saved_triage.issue_category_label == "Burner Will Not Start"
        assert saved_triage.serial_number == "J123456"
        assert saved_triage.has_serial_number is True

    @pytest.mark.asyncio
    async def test_serial_stripped_when_has_serial_number_false(self, use_case, valid_dto, mock_triage_repository):
        valid_dto.has_serial_number = False
        await use_case.execute(valid_dto)
        saved_triage = mock_triage_repository.save.call_args[0][0]
        assert saved_triage.serial_number is None

    @pytest.mark.asyncio
    async def test_category_g_preserves_free_text(self, use_case, valid_dto, mock_triage_repository):
        valid_dto.issue_category = "G"
        valid_dto.issue_free_text = "Unusual smell from the burner"
        await use_case.execute(valid_dto)
        saved_triage = mock_triage_repository.save.call_args[0][0]
        assert saved_triage.issue_free_text == "Unusual smell from the burner"

    @pytest.mark.asyncio
    async def test_non_g_category_discards_free_text(self, use_case, valid_dto, mock_triage_repository):
        valid_dto.issue_category = "A"
        valid_dto.issue_free_text = "should be discarded"
        await use_case.execute(valid_dto)
        saved_triage = mock_triage_repository.save.call_args[0][0]
        assert saved_triage.issue_free_text is None

    @pytest.mark.asyncio
    async def test_follow_up_answers_saved(self, use_case, valid_dto, mock_triage_repository):
        valid_dto.follow_up_answers = {"has_power": "Yes", "fault_codes": "E1"}
        await use_case.execute(valid_dto)
        saved_triage = mock_triage_repository.save.call_args[0][0]
        assert saved_triage.follow_up_answers == {"has_power": "Yes", "fault_codes": "E1"}

    @pytest.mark.asyncio
    async def test_context_summary_in_response(self, use_case, valid_dto):
        result = await use_case.execute(valid_dto)
        assert "TX Series" in result.context_summary
        assert "Burner Will Not Start" in result.context_summary

    @pytest.mark.asyncio
    async def test_result_contains_created_at(self, use_case, valid_dto):
        result = await use_case.execute(valid_dto)
        assert isinstance(result.created_at, datetime)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("category", ["A", "B", "C", "D", "E", "F", "G"])
    async def test_all_issue_categories_accepted(self, use_case, valid_dto, category):
        valid_dto.issue_category = category
        result = await use_case.execute(valid_dto)
        assert result.issue_category == category

    # ─── Validation Errors ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_raises_invalid_category(self, use_case, valid_dto):
        valid_dto.issue_category = "Z"
        with pytest.raises(ValueError, match="Invalid issue category"):
            await use_case.execute(valid_dto)

    @pytest.mark.asyncio
    async def test_raises_empty_category(self, use_case, valid_dto):
        valid_dto.issue_category = ""
        with pytest.raises(ValueError, match="Invalid issue category"):
            await use_case.execute(valid_dto)

    @pytest.mark.asyncio
    async def test_raises_invalid_burner_series(self, use_case, valid_dto):
        valid_dto.burner_series = "XX"
        with pytest.raises(ValueError, match="Invalid burner series"):
            await use_case.execute(valid_dto)

    @pytest.mark.asyncio
    async def test_no_error_when_burner_series_none(self, use_case, valid_dto):
        valid_dto.burner_series = None
        result = await use_case.execute(valid_dto)
        assert result.burner_series is None

    @pytest.mark.asyncio
    async def test_raises_invalid_serial_format(self, use_case, valid_dto):
        valid_dto.has_serial_number = True
        valid_dto.serial_number = "1INVALID"
        with pytest.raises(ValueError, match="Invalid serial number format"):
            await use_case.execute(valid_dto)

    @pytest.mark.asyncio
    async def test_raises_serial_with_letters_after_prefix(self, use_case, valid_dto):
        valid_dto.has_serial_number = True
        valid_dto.serial_number = "JXX123"
        with pytest.raises(ValueError, match="Invalid serial number format"):
            await use_case.execute(valid_dto)

    @pytest.mark.asyncio
    async def test_no_serial_validation_when_has_serial_false(self, use_case, valid_dto):
        valid_dto.has_serial_number = False
        valid_dto.serial_number = "INVALID"
        result = await use_case.execute(valid_dto)
        assert isinstance(result, TriageResponseDTO)

    @pytest.mark.asyncio
    async def test_no_serial_validation_when_serial_none(self, use_case, valid_dto):
        valid_dto.has_serial_number = True
        valid_dto.serial_number = None
        result = await use_case.execute(valid_dto)
        assert isinstance(result, TriageResponseDTO)

    @pytest.mark.asyncio
    async def test_raises_session_not_found(self, use_case, valid_dto, mock_session_repository):
        valid_dto.session_id = "ghost-999"
        mock_session_repository.find_by_id.return_value = None
        with pytest.raises(ValueError, match="ghost-999"):
            await use_case.execute(valid_dto)

    @pytest.mark.asyncio
    async def test_raises_session_already_has_triage(self, use_case, valid_dto, mock_triage_repository):
        valid_dto.session_id = "session-existing-001"
        now = datetime.now(UTC)
        mock_triage_repository.find_by_session_id.return_value = ChatTriage(
            id="existing-triage",
            session_id="session-existing-001",
            user_id="user-123",
            burner_series="TX",
            burner_identified_via="direct_selection",
            serial_number=None,
            has_serial_number=False,
            issue_category="A",
            issue_category_label="Burner Will Not Start",
            issue_free_text=None,
            follow_up_answers={},
            created_at=now,
        )
        with pytest.raises(ValueError, match="already has a triage record"):
            await use_case.execute(valid_dto)

    @pytest.mark.asyncio
    async def test_no_repo_calls_before_validation_error(self, use_case, valid_dto, mock_session_repository, mock_triage_repository):
        valid_dto.issue_category = "Z"
        with pytest.raises(ValueError, match="Invalid issue category"):
            await use_case.execute(valid_dto)
        mock_session_repository.find_by_id.assert_not_called()
        mock_session_repository.create.assert_not_called()
        mock_triage_repository.save.assert_not_called()

    # ─── Ticket auto-creation ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_ticket_created_for_new_session(
        self, use_case, valid_dto, mock_ticket_repository, mock_ticket_activity_repository
    ):
        """Submitting triage with no session_id creates a ticket assigned to lmbot"""
        await use_case.execute(valid_dto)

        mock_ticket_repository.save.assert_called_once()
        saved_ticket = mock_ticket_repository.save.call_args[0][0]
        assert saved_ticket.user_id == "user-123"
        assert saved_ticket.status == "open"
        assert saved_ticket.assigned_to == "lmbot"
        assert saved_ticket.session_id == "session-new-001"

        mock_ticket_activity_repository.save.assert_called_once()
        saved_activity = mock_ticket_activity_repository.save.call_args[0][0]
        assert saved_activity.action == "created"
        assert saved_activity.actor == "lmbot"

    @pytest.mark.asyncio
    async def test_ticket_not_created_for_existing_session(
        self, use_case, valid_dto, mock_ticket_repository
    ):
        """Attaching triage to an existing session does not create a new ticket"""
        valid_dto.session_id = "session-existing-001"
        await use_case.execute(valid_dto)

        mock_ticket_repository.save.assert_not_called()
