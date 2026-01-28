import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from app.application.use_cases.chatbot.process_chat_query import ProcessChatQuery
from app.application.dtos.chat_dtos import ChatQueryDTO, ChatResponseDTO
from app.domain.entities.chat_message import ChatMessage


class TestProcessChatQuery:
    """Test ProcessChatQuery use case"""
    
    @pytest.fixture
    def mock_chat_repository(self):
        """Mock chat repository"""
        repo = AsyncMock()
        repo.save.return_value = ChatMessage(
            id="msg-123",
            user_id="user-123",
            query="What is task decomposition?",
            response="Task decomposition is a technique...",
            source_document_ids=["doc-1", "doc-2"],
            created_at=datetime.utcnow()
        )
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
    def use_case(self, mock_chat_repository, mock_vector_store, mock_llm_service):
        """Create use case with mocked dependencies"""
        return ProcessChatQuery(
            chat_repository=mock_chat_repository,
            vector_store_repository=mock_vector_store,
            llm_service=mock_llm_service
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
            {"id": "2", "document_id": "doc-2", "content": "Low relevance", "similarity_score": 0.50, "metadata": {}},
        ]
        
        dto = ChatQueryDTO(user_id="user-123", query="Test query")
        
        # Act
        result = await use_case.execute(dto)
        
        # Assert - should only include high similarity sources
        assert len(result.sources) == 1
        assert result.sources[0]["similarity_score"] >= 0.7
    
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