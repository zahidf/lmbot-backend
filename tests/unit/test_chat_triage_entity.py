import pytest
from datetime import datetime, UTC
from app.domain.entities.chat_triage import ChatTriage


class TestChatTriage:

    def _make_triage(self, **overrides) -> ChatTriage:
        defaults = dict(
            id="triage-001",
            session_id="session-001",
            user_id="user-001",
            burner_series="TX",
            burner_identified_via="direct_selection",
            serial_number="J123456",
            has_serial_number=True,
            issue_category="A",
            issue_category_label="Burner Will Not Start",
            issue_free_text=None,
            follow_up_answers={},
            created_at=datetime.now(UTC),
        )
        defaults.update(overrides)
        return ChatTriage(**defaults)

    # Is complete validation

    def test_is_complete_with_known_series_and_valid_category(self):
        triage = self._make_triage(burner_series="TX", issue_category="A")
        assert triage.is_complete() is True

    def test_is_complete_when_identified_via_unknown_no_series(self):
        triage = self._make_triage(burner_series=None, burner_identified_via="unknown")
        assert triage.is_complete() is True

    def test_is_not_complete_when_no_series_and_not_unknown(self):
        triage = self._make_triage(
            burner_series=None, burner_identified_via="direct_selection"
        )
        assert triage.is_complete() is False

    def test_is_not_complete_when_category_empty(self):
        triage = self._make_triage(issue_category="")
        assert triage.is_complete() is False

    def test_is_not_complete_when_category_invalid(self):
        triage = self._make_triage(issue_category="Z")
        assert triage.is_complete() is False

    @pytest.mark.parametrize("category", ["A", "B", "C", "D", "E", "F", "G"])
    def test_is_complete_all_valid_categories(self, category):
        triage = self._make_triage(
            issue_category=category,
            issue_category_label=ChatTriage.ISSUE_CATEGORIES[category],
        )
        assert triage.is_complete() is True

    # Serial Number Validation

    def test_valid_serial(self):
        assert ChatTriage.validate_serial_number("J123456") is True

    def test_valid_single_letter_prefix(self):
        assert ChatTriage.validate_serial_number("A1") is True

    def test_valid_uppercase(self):
        assert ChatTriage.validate_serial_number("Z9999") is True

    def test_valid_lowercase_prefix(self):
        assert ChatTriage.validate_serial_number("j123456") is True

    def test_invalid_empty_string(self):
        assert ChatTriage.validate_serial_number("") is False

    def test_invalid_single_char(self):
        assert ChatTriage.validate_serial_number("J") is False

    def test_invalid_starts_with_digit(self):
        assert ChatTriage.validate_serial_number("1234567") is False

    def test_invalid_letters_after_prefix(self):
        assert ChatTriage.validate_serial_number("J12X56") is False

    def test_invalid_special_characters(self):
        assert ChatTriage.validate_serial_number("J-123") is False

    def test_invalid_two_letter_prefix(self):
        assert ChatTriage.validate_serial_number("JK123") is False

    # Get Context Summary

    def test_summary_known_burner_with_serial(self):
        triage = self._make_triage(
            burner_series="TX",
            serial_number="J123456",
            has_serial_number=True,
            issue_category="A",
            issue_category_label="Burner Will Not Start",
        )
        summary = triage.get_context_summary()
        assert "TX Series" in summary
        assert "Serial Number: J123456" in summary
        assert "Burner Will Not Start" in summary
        assert "Issue Description" not in summary
        assert "Additional Details" not in summary

    def test_summary_unknown_burner(self):
        triage = self._make_triage(burner_series=None, burner_identified_via="unknown")
        summary = triage.get_context_summary()
        assert "Unknown / Not identified" in summary

    def test_summary_no_serial(self):
        triage = self._make_triage(has_serial_number=False, serial_number=None)
        summary = triage.get_context_summary()
        assert "Serial Number: Not provided" in summary

    def test_summary_category_g_with_free_text(self):
        triage = self._make_triage(
            issue_category="G",
            issue_category_label="Something Else",
            issue_free_text="Unusual smell from the burner",
        )
        summary = triage.get_context_summary()
        assert "Something Else" in summary
        assert "Issue Description: Unusual smell from the burner" in summary

    def test_summary_category_g_without_free_text(self):
        triage = self._make_triage(
            issue_category="G",
            issue_category_label="Something Else",
            issue_free_text=None,
        )
        summary = triage.get_context_summary()
        assert "Issue Description" not in summary

    def test_summary_with_follow_up_answers(self):
        triage = self._make_triage(
            follow_up_answers={"has_power": "Yes", "fault_codes": "E1"}
        )
        summary = triage.get_context_summary()
        assert "Additional Details:" in summary
        assert "has_power: Yes" in summary
        assert "fault_codes: E1" in summary

    def test_summary_non_g_category_ignores_free_text(self):
        triage = self._make_triage(
            issue_category="A",
            issue_category_label="Burner Will Not Start",
            issue_free_text="should be ignored",
        )
        summary = triage.get_context_summary()
        assert "should be ignored" not in summary

    def test_summary_returns_string(self):
        triage = self._make_triage()
        assert isinstance(triage.get_context_summary(), str)

    # Module-level constants

    def test_issue_categories_has_all_keys(self):
        assert set(ChatTriage.ISSUE_CATEGORIES.keys()) == {
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
        }

    def test_burner_series_contains_expected_values(self):
        assert set(ChatTriage.BURNER_SERIES) == {"FD", "TX", "DB", "FDB"}
