from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ChatTriage:
    """
    Chat triage entity representing the initial intake questionnaire
    completed before a chat session begins.

    Captures:
    - Burner model selection
    - Serial number (optional)
    - Issue category
    - Category-specific details
    """

    # Issue category options
    # currently constants, in the future, the below categories/data will be stored in database, changeable by admin
    ISSUE_CATEGORIES = {
        "A": "Burner Will Not Start",
        "B": "Burner Starts Then Locks Out",
        "C": "Burner Running Poorly",
        "D": "Installation/Commissioning Question",
        "E": "Documentation Request",
        "F": "Spare Parts",
        "G": "Something Else",
    }

    BURNER_SERIES = {
        "FD": "FD Series",
        "TX": "TX Series",
        "DB": "DB Series",
        "FDB": "FDB Series",
    }

    id: Optional[str]
    session_id: str
    user_id: str

    # Q1: Burner model
    burner_series: Optional[str]  # FD, TX, DB, FDB or None if truly unknown
    burner_identified_via: (
        str  # "direct_selection" | "image_identification" | "unknown"
    )

    # Q2: Serial number
    serial_number: Optional[str]
    has_serial_number: bool

    # Q3: Issue category
    issue_category: str  # A-G
    issue_category_label: Optional[str]

    # Q3b: Free text for "Something Else"
    issue_free_text: Optional[str]

    # Q4: Problem-specific follow-up answers (stored as JSON)
    follow_up_answers: Dict[str, Any] = field(default_factory=dict)

    created_at: Optional[datetime] = None

    def is_complete(self) -> bool:
        """Check if triage is fully completed"""
        has_burner = (
            self.burner_series is not None or self.burner_identified_via == "unknown"
        )
        has_issue = self.issue_category in self.ISSUE_CATEGORIES
        return has_burner and has_issue

    def get_context_summary(self) -> str:
        """
        Generate a plain-text summary of the triage for injection
        into the LLM system prompt / context.
        """
        parts = []

        # Burner info
        if self.burner_series:
            parts.append(f"Burner Model: {self.burner_series} Series")
        else:
            parts.append("Burner Model: Unknown / Not identified")

        # Serial number
        if self.has_serial_number and self.serial_number:
            parts.append(f"Serial Number: {self.serial_number}")
        else:
            parts.append("Serial Number: Not provided")

        # Issue
        category_label = self.ISSUE_CATEGORIES.get(self.issue_category, "Unknown")
        parts.append(f"Issue Category: {category_label}")

        if self.issue_category == "G" and self.issue_free_text:
            parts.append(f"Issue Description: {self.issue_free_text}")

        # Follow-up details
        if self.follow_up_answers:
            parts.append("Additional Details:")
            for key, value in self.follow_up_answers.items():
                parts.append(f"  - {key}: {value}")

        return "\n".join(parts)

    @staticmethod
    def validate_serial_number(serial: str) -> bool:
        """
        Basic validation of serial number format.
        Expected format: letter followed by digits, e.g. J123456
        """
        if not serial or len(serial) < 2:
            return False
        return serial[0].isalpha() and serial[1:].isdigit()
