import pytest


class TestChatSessionsAPI:
    """End-to-end tests for chat session management endpoints"""

    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def session_id(self, client, auth_headers):
        """Create a real chat session by sending a query, return its session_id"""
        response = client.post(
            "/api/v1/chat/query",
            json={"query": "TX Series installation procedure steps"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        return response.json()["session_id"]

    # ── List sessions ────────────────────────────────────────────

    def test_list_sessions_returns_sessions(self, client, auth_headers, session_id):
        """Sessions list includes the session created by the fixture"""
        response = client.get("/api/v1/chat/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "sessions" in data
        assert "total" in data
        assert isinstance(data["sessions"], list)
        assert data["total"] >= 1

        for s in data["sessions"]:
            assert "id" in s
            assert "title" in s
            assert "created_at" in s
            assert "updated_at" in s

    def test_list_sessions_with_pagination(self, client, auth_headers, session_id):
        """limit=1 returns at most one session"""
        response = client.get(
            "/api/v1/chat/sessions?limit=1&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) <= 1

    def test_list_sessions_limit_clamped(self, client, auth_headers):
        """limit > 100 is silently clamped to 100 (no validation error)"""
        response = client.get(
            "/api/v1/chat/sessions?limit=200",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_list_sessions_unauthenticated(self, client):
        """Session list requires authentication"""
        response = client.get("/api/v1/chat/sessions")
        assert response.status_code == 401

    # ── Get session by ID ────────────────────────────────────────

    def test_get_session_by_id_success(self, client, auth_headers, session_id):
        """Fetching an existing session returns its detail with messages"""
        response = client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == session_id
        assert "title" in data
        assert "messages" in data
        assert "created_at" in data
        assert "updated_at" in data

        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 1

        msg = data["messages"][0]
        assert "message_id" in msg
        assert "session_id" in msg
        assert "query" in msg
        assert "response" in msg
        assert "sources" in msg
        assert "created_at" in msg

    def test_get_session_by_id_not_found(self, client, auth_headers):
        """Non-existent session_id returns 404"""
        response = client.get(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Chat session not found" in response.json()["detail"]

    def test_get_session_by_id_unauthenticated(self, client):
        """Fetching session requires authentication"""
        response = client.get(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

    # ── Update session title ─────────────────────────────────────

    def test_patch_session_title_success(self, client, auth_headers, session_id):
        """Session title can be updated via PATCH"""
        response = client.patch(
            f"/api/v1/chat/sessions/{session_id}",
            json={"title": "Updated Session Title"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == session_id
        assert data["title"] == "Updated Session Title"
        assert "created_at" in data
        assert "updated_at" in data

    def test_patch_session_title_not_found(self, client, auth_headers):
        """Patching a non-existent session returns 404"""
        response = client.patch(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000",
            json={"title": "Some Title"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Chat session not found" in response.json()["detail"]

    def test_patch_session_unauthenticated(self, client):
        """Patching session requires authentication"""
        response = client.patch(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000",
            json={"title": "Title"},
        )
        assert response.status_code == 401

    # ── Delete session ───────────────────────────────────────────

    def test_delete_session_success(self, client, auth_headers):
        """Deleting a session returns success message with the session id"""
        # Create a dedicated session for deletion
        create_response = client.post(
            "/api/v1/chat/query",
            json={"query": "FD Series maintenance guide"},
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        sid = create_response.json()["session_id"]

        response = client.delete(
            f"/api/v1/chat/sessions/{sid}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Chat session deleted successfully"
        assert data["id"] == sid

    def test_delete_session_not_found(self, client, auth_headers):
        """Deleting a non-existent session returns 404"""
        response = client.delete(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Chat session not found" in response.json()["detail"]

    def test_delete_session_unauthenticated(self, client):
        """Deleting session requires authentication"""
        response = client.delete(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401

    def test_session_is_gone_after_delete(self, client, auth_headers):
        """After deletion the session is no longer retrievable"""
        create_response = client.post(
            "/api/v1/chat/query",
            json={"query": "HC Series commissioning steps"},
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        sid = create_response.json()["session_id"]

        client.delete(f"/api/v1/chat/sessions/{sid}", headers=auth_headers)

        get_response = client.get(
            f"/api/v1/chat/sessions/{sid}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    # ── Session messages ordering ────────────────────────────────

    def test_session_messages_ordered_chronologically(
        self, client, auth_headers, session_id
    ):
        """Messages within a session are returned oldest-first"""
        # Send a second query to the same session
        client.post(
            "/api/v1/chat/query",
            json={"query": "TX Series spare parts list", "session_id": session_id},
            headers=auth_headers,
        )

        response = client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        messages = response.json()["messages"]
        assert len(messages) >= 2

        # created_at should be non-decreasing
        for i in range(1, len(messages)):
            assert messages[i - 1]["created_at"] <= messages[i]["created_at"]

    # ── Chat query with existing session ────────────────────────

    def test_chat_query_with_existing_session_id(
        self, client, auth_headers, session_id
    ):
        """POST /chat/query with an existing session_id reuses that session"""
        response = client.post(
            "/api/v1/chat/query",
            json={
                "query": "What is the ignition sequence for TX Series?",
                "session_id": session_id,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
