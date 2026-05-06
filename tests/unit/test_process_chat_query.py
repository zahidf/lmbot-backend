import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from app.application.use_cases.chatbot.process_chat_query import ProcessChatQuery
from app.application.dtos.chat_dtos import ChatQueryDTO, ChatResponseDTO
from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.ticket import Ticket


class TestProcessChatQuery:
    """Test ProcessChatQuery use case"""

    @pytest.fixture
    def mock_chat_repository(self):
        """Mock chat repository"""
        repo = AsyncMock()
        repo.save.return_value = ChatMessage(
            id="msg-123",
            user_id="user-123",
            session_id="session-123",
            query="What is task decomposition?",
            response="Task decomposition is a technique...",
            source_document_ids=["doc-1", "doc-2"],
            created_at=datetime.now(UTC)
        )
        return repo

    @pytest.fixture
    def mock_chat_session_repository(self):
        """Mock chat session repository"""
        repo = AsyncMock()
        repo.create.return_value = ChatSession(
            id="session-123",
            user_id="user-123",
            title="What is task decomposition?",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        return repo

    @pytest.fixture
    def mock_triage_repository(self):
        """Mock triage repository"""
        repo = AsyncMock()
        repo.find_by_session_id.return_value = None
        return repo

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store repository"""
        repo = AsyncMock()
        repo.similarity_search.return_value = [
            {
                "id": "chunk-1",
                "document_id": "doc-1",
                "content": "Task decomposition can be done in three ways: (1) by LLM with simple prompting...",
                "similarity_score": 0.92,
                "metadata": {"source": "blog-post"}
            },
            {
                "id": "chunk-2",
                "document_id": "doc-2",
                "content": "Common extensions include Chain of Thought and Tree of Thoughts...",
                "similarity_score": 0.87,
                "metadata": {"source": "blog-post"}
            }
        ]
        return repo

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service"""
        service = AsyncMock()
        service.generate_embedding.return_value = [0.1] * 1536  # Mock embedding
        service.generate_response.return_value = (
            "Task decomposition is a technique used to break down complex tasks "
            "into smaller, manageable steps. It can be done through prompting techniques "
            "like Chain of Thought."
        )
        return service

    @pytest.fixture
    def mock_ticket_repository(self):
        """Mock ticket repository"""
        repo = AsyncMock()
        ticket = Ticket(
            id="ticket-123",
            session_id="session-123",
            user_id="user-123",
            summary=None,
            status="open",
            assigned_to="lmbot",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        repo.save.return_value = ticket
        repo.find_by_session_id.return_value = ticket
        return repo

    @pytest.fixture
    def mock_ticket_activity_repository(self):
        """Mock ticket activity repository"""
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_chat_repository, mock_chat_session_repository, mock_triage_repository, mock_vector_store, mock_llm_service, mock_ticket_repository, mock_ticket_activity_repository):
        """Create use case with mocked dependencies"""
        return ProcessChatQuery(
            chat_repository=mock_chat_repository,
            chat_session_repository=mock_chat_session_repository,
            triage_repository=mock_triage_repository,
            vector_store_repository=mock_vector_store,
            llm_service=mock_llm_service,
            ticket_repository=mock_ticket_repository,
            ticket_activity_repository=mock_ticket_activity_repository,
        )
    
    @pytest.mark.asyncio
    async def test_process_simple_query(self, use_case, mock_llm_service, mock_vector_store):
        """Test processing a simple query"""
        # Arrange
        dto = ChatQueryDTO(
            user_id="user-123",
            query="What is task decomposition?"
        )
        
        # Act
        result = await use_case.execute(dto)
        
        # Assert
        assert isinstance(result, ChatResponseDTO)
        assert result.query == "What is task decomposition?"
        assert result.response is not None
        assert len(result.response) > 0
        assert len(result.sources) > 0
        
        # Verify service calls
        mock_llm_service.generate_embedding.assert_called_once_with(dto.query)
        mock_vector_store.similarity_search.assert_called_once()
        mock_llm_service.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_query_with_high_similarity_threshold(self, use_case, mock_vector_store):
        """Test that only high-similarity documents are used"""
        # Arrange
        mock_vector_store.similarity_search.return_value = [
            {"id": "1", "document_id": "doc-1", "content": "High relevance", "similarity_score": 0.85, "metadata": {}},
            {"id": "2", "document_id": "doc-2", "content": "Low relevance", "similarity_score": 0.20, "metadata": {}},
        ]

        dto = ChatQueryDTO(user_id="user-123", query="Test query")

        # Act
        result = await use_case.execute(dto)

        # Assert - should only include sources above SIMILARITY_THRESHOLD (0.3)
        assert len(result.sources) == 1
        assert result.sources[0]["similarity_score"] >= 0.3
    
    @pytest.mark.asyncio
    async def test_process_query_no_relevant_documents(self, use_case, mock_vector_store):
        """Test handling when no relevant documents are found"""
        # Arrange
        mock_vector_store.similarity_search.return_value = []
        dto = ChatQueryDTO(user_id="user-123", query="Unknown topic")
        
        # Act
        result = await use_case.execute(dto)
        
        # Assert
        assert "couldn't find relevant information" in result.response.lower()
        assert len(result.sources) == 0
    
    @pytest.mark.asyncio
    async def test_saves_chat_message(self, use_case, mock_chat_repository):
        """Test that chat message is saved to repository"""
        # Arrange
        dto = ChatQueryDTO(user_id="user-123", query="Test query")

        # Act
        await use_case.execute(dto)

        # Assert
        mock_chat_repository.save.assert_called_once()
        saved_message = mock_chat_repository.save.call_args[0][0]
        assert saved_message.user_id == "user-123"
        assert saved_message.query == "Test query"

    @pytest.mark.asyncio
    async def test_process_query_session_not_found(
        self, use_case, mock_chat_session_repository
    ):
        """Providing a session_id that doesn't exist raises ValueError"""
        mock_chat_session_repository.find_by_id.return_value = None

        dto = ChatQueryDTO(
            user_id="user-123",
            query="Test query",
            session_id="nonexistent-session-id",
        )

        with pytest.raises(ValueError, match="not found"):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_process_query_triage_applies_burner_filter(
        self, use_case, mock_triage_repository, mock_vector_store
    ):
        """Triage with a burner_series auto-applies product_series filter to the search"""
        triage = MagicMock()
        triage.burner_series = "TX"
        triage.get_context_summary.return_value = "Burner Model: TX Series"
        mock_triage_repository.find_by_session_id.return_value = triage

        dto = ChatQueryDTO(user_id="user-123", query="How to install TX burner?")
        await use_case.execute(dto)

        call_kwargs = mock_vector_store.similarity_search.call_args.kwargs
        assert call_kwargs["filters"]["product_series"] == "TX"

    @pytest.mark.asyncio
    async def test_process_query_triage_context_enriches_prompt(
        self, use_case, mock_triage_repository, mock_llm_service
    ):
        """When triage context exists, the LLM is called with an enriched prompt"""
        triage = MagicMock()
        triage.burner_series = "FD"
        triage.get_context_summary.return_value = (
            "Burner Model: FD Series\nIssue Category: Burner Starts Then Locks Out"
        )
        mock_triage_repository.find_by_session_id.return_value = triage

        dto = ChatQueryDTO(user_id="user-123", query="Why is my burner locking out?")
        await use_case.execute(dto)

        call_kwargs = mock_llm_service.generate_response.call_args.kwargs
        enriched = call_kwargs["query"]
        assert "[Customer Background from Triage]" in enriched
        assert "Burner Model: FD Series" in enriched
        assert "[Customer Question]" in enriched

    # ─── Ticket auto-creation ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_ticket_created_on_new_session(
        self, use_case, mock_ticket_repository, mock_ticket_activity_repository
    ):
        """A new session triggers ticket + activity creation"""
        dto = ChatQueryDTO(user_id="user-123", query="Test query")
        await use_case.execute(dto)

        mock_ticket_repository.save.assert_called_once()
        saved_ticket = mock_ticket_repository.save.call_args[0][0]
        assert saved_ticket.user_id == "user-123"
        assert saved_ticket.status == "open"
        assert saved_ticket.assigned_to == "lmbot"
        mock_ticket_activity_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_ticket_not_created_for_existing_session(
        self, use_case, mock_chat_session_repository, mock_ticket_repository
    ):
        """Providing an existing session_id does not create a ticket"""
        mock_chat_session_repository.find_by_id.return_value = ChatSession(
            id="session-existing",
            user_id="user-123",
            title="Existing session",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        dto = ChatQueryDTO(user_id="user-123", query="Test query", session_id="session-existing")
        await use_case.execute(dto)

        mock_ticket_repository.save.assert_not_called()

    # ─── can_escalate detection ───────────────────────────────

    @pytest.mark.asyncio
    async def test_can_escalate_true_when_no_relevant_chunks(
        self, use_case, mock_vector_store, mock_ticket_repository
    ):
        """Empty retrieval results set can_escalate=True and populates ticket_id"""
        mock_vector_store.similarity_search.return_value = []
        dto = ChatQueryDTO(user_id="user-123", query="Unknown topic")

        result = await use_case.execute(dto)

        assert result.can_escalate is True
        assert result.ticket_id == "ticket-123"

    @pytest.mark.asyncio
    async def test_can_escalate_true_when_llm_cannot_answer(
        self, use_case, mock_llm_service, mock_ticket_repository
    ):
        """LLM response containing a cannot-answer phrase triggers can_escalate=True"""
        mock_llm_service.generate_response.return_value = (
            "I don't have enough information to answer your question accurately."
        )
        dto = ChatQueryDTO(user_id="user-123", query="Obscure topic")

        result = await use_case.execute(dto)

        assert result.can_escalate is True
        assert result.ticket_id == "ticket-123"

    @pytest.mark.asyncio
    async def test_can_escalate_false_for_normal_response(
        self, use_case, mock_llm_service, mock_ticket_repository
    ):
        """A clear LLM response sets can_escalate=False and ticket_id=None"""
        mock_llm_service.generate_response.return_value = (
            "The TX series burner uses a forced-draught combustion system."
        )
        dto = ChatQueryDTO(user_id="user-123", query="How does TX burner work?")

        result = await use_case.execute(dto)

        assert result.can_escalate is False
        assert result.ticket_id is None
        mock_ticket_repository.find_by_session_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_ticket_id_none_when_ticket_missing(
        self, use_case, mock_vector_store, mock_ticket_repository
    ):
        """If no ticket exists for the session, ticket_id is None even when can_escalate=True"""
        mock_vector_store.similarity_search.return_value = []
        mock_ticket_repository.find_by_session_id.return_value = None
        dto = ChatQueryDTO(user_id="user-123", query="Unknown topic")

        result = await use_case.execute(dto)

        assert result.can_escalate is True
        assert result.ticket_id is None