import pytest
from datetime import datetime, UTC
from app.domain.entities.chat_session import ChatSession


class TestChatSession:

    # Construction
    def test_create_with_all_fields(self):
        now = datetime.now(UTC)
        session = ChatSession(
            id="session-abc",
            user_id="user-123",
            title="TX Series — Burner Will Not Start",
            created_at=now,
            updated_at=now,
        )
        assert session.id == "session-abc"
        assert session.user_id == "user-123"
        assert session.title == "TX Series — Burner Will Not Start"
        assert session.created_at == now
        assert session.updated_at == now

    def test_create_with_none_id(self):
        now = datetime.now(UTC)
        session = ChatSession(id=None, user_id="user-123", title="Test", created_at=now, updated_at=now)
        assert session.id is None

    def test_create_with_none_title(self):
        now = datetime.now(UTC)
        session = ChatSession(id="s1", user_id="user-123", title=None, created_at=now, updated_at=now)
        assert session.title is None

    # Title update

    def _make_session(self) -> ChatSession:
        now = datetime.now(UTC)
        return ChatSession(id="s1", user_id="user-1", title="Old Title", created_at=now, updated_at=now)

    def test_update_title_short(self):
        session = self._make_session()
        session.update_title("New Title")
        assert session.title == "New Title"

    def test_update_title_truncates_at_500_chars(self):
        session = self._make_session()
        long_title = "x" * 501
        session.update_title(long_title)
        assert len(session.title) == 500
        assert session.title == "x" * 500

    def test_update_title_exactly_500_not_truncated(self):
        session = self._make_session()
        exact_title = "a" * 500
        session.update_title(exact_title)
        assert len(session.title) == 500
        assert session.title == exact_title

    def test_update_title_with_empty_string_sets_none(self):
        session = self._make_session()
        session.update_title("")
        assert session.title is None

    def test_update_title_with_none_sets_none(self):
        session = self._make_session()
        session.update_title(None)
        assert session.title is None

    # Title generation

    def test_generate_title_short_query(self):
        query = "What is wrong with my burner?"
        result = ChatSession.generate_title_from_query(query)
        assert result == query.strip()
        assert "..." not in result

    def test_generate_title_exactly_100_chars(self):
        query = "a" * 100
        result = ChatSession.generate_title_from_query(query)
        assert result == query
        assert "..." not in result

    def test_generate_title_truncates_at_100(self):
        query = "b" * 101
        result = ChatSession.generate_title_from_query(query)
        assert len(result) == 100
        assert result.endswith("...")
        assert result == "b" * 97 + "..."

    def test_generate_title_long_query(self):
        query = "c" * 200
        result = ChatSession.generate_title_from_query(query)
        assert len(result) == 100
        assert result.endswith("...")

    def test_generate_title_strips_whitespace(self):
        query = "  What is wrong with my burner?  "
        result = ChatSession.generate_title_from_query(query)
        assert not result.startswith(" ")
        assert not result.endswith(" ")
        assert result == query.strip()

    def test_generate_title_returns_string(self):
        result = ChatSession.generate_title_from_query("My burner won't start")
        assert isinstance(result, str)
