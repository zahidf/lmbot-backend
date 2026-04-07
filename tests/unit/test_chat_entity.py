import pytest
from datetime import datetime, UTC
from app.domain.entities.chat_message import ChatMessage


class TestChatMessage:
    """Test ChatMessage entity"""
    
    def test_create_chat_message(self):
        """Test creating a chat message"""
        message = ChatMessage(
            id="test-id",
            user_id="user-123",
            session_id="session-123",
            query="What is task decomposition?",
            response="Task decomposition is...",
            source_document_ids=["doc-1", "doc-2"],
            created_at=datetime.now(UTC)
        )

        assert message.id == "test-id"
        assert message.user_id == "user-123"
        assert message.query == "What is task decomposition?"
        assert len(message.source_document_ids) == 2
    
    def test_has_sources(self):
        """Test checking if message has sources"""
        message = ChatMessage(
            id="test-id",
            user_id="user-123",
            session_id="session-123",
            query="Test query",
            response="Test response",
            source_document_ids=["doc-1"],
            created_at=datetime.now(UTC)
        )

        assert message.has_sources() is True
    
    def test_no_sources(self):
        """Test message without sources"""
        message = ChatMessage(
            id="test-id",
            user_id="user-123",
            session_id="session-123",
            query="Test query",
            response="Test response",
            source_document_ids=[],
            created_at=datetime.now(UTC)
        )

        assert message.has_sources() is False