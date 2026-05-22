import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestChatbotAPI:
    """End-to-end tests for chatbot API"""

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"Authorization": "Bearer test-token"}

    def test_chat_query_success(self, auth_headers):
        """Test successful chat query"""
        # Arrange
        payload = {"query": "What is task decomposition?"}

        # Act
        response = client.post("/api/v1/chat/query", json=payload, headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "message_id" in data
        assert "query" in data
        assert "response" in data
        assert "sources" in data
        assert "created_at" in data

        assert data["query"] == payload["query"]
        assert len(data["response"]) > 0
        assert isinstance(data["sources"], list)

    def test_chat_query_with_sources(self, auth_headers):
        """Test that response includes source citations"""
        # Arrange
        payload = {"query": "How do I maintain TX Series burners?"}

        # Act
        response = client.post("/api/v1/chat/query", json=payload, headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check sources structure
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            assert "document_id" in source
            assert "content" in source
            assert "similarity_score" in source
            assert "metadata" in source
            assert source["similarity_score"] > 0

    def test_chat_query_empty_query(self, auth_headers):
        """Test validation for empty query"""
        # Arrange
        payload = {"query": ""}

        # Act
        response = client.post("/api/v1/chat/query", json=payload, headers=auth_headers)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_chat_query_unauthenticated(self):
        """Test that authentication is required"""
        # Arrange
        payload = {"query": "Test query"}

        # Act
        response = client.post("/api/v1/chat/query", json=payload)

        # Assert
        assert response.status_code == 401  # Unauthorized

    def test_get_chat_history(self, auth_headers):
        """Test retrieving chat history"""
        # Act
        response = client.get("/api/v1/chat/history", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "messages" in data
        assert isinstance(data["messages"], list)
