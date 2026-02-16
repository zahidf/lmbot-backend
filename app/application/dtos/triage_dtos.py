from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class TriageSubmissionDTO:
    """Input DTO for submitting completed triage"""
    user_id: str
    session_id: Optional[str]  # None = create new session
    
    # Q1
    burner_series: Optional[str]
    burner_identified_via: str  # "direct_selection" | "image_identification" | "unknown"
    
    # Q2
    serial_number: Optional[str]
    has_serial_number: bool
    
    # Q3
    issue_category: str
    issue_free_text: Optional[str] = None
    
    # Q4
    follow_up_answers: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriageResponseDTO:
    """Output DTO after triage is saved"""
    triage_id: str
    session_id: str
    burner_series: Optional[str]
    serial_number: Optional[str]
    issue_category: str
    issue_category_label: str
    context_summary: str
    created_at: datetime


@dataclass
class TriageFollowUpPrompt:
    """Describes a follow-up question for a specific issue category"""
    question: str
    field_key: str
    input_type: str  # "buttons" | "text" | "select"
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None


# ─── Category-specific follow-up prompts ─────────────────────

CATEGORY_FOLLOW_UPS: Dict[str, List[TriageFollowUpPrompt]] = {
    "A": [  # Burner Will Not Start
        TriageFollowUpPrompt(
            question="Is there power to the burner control panel?",
            field_key="has_power",
            input_type="buttons",
            options=["Yes", "No", "Not Sure"],
        ),
        TriageFollowUpPrompt(
            question="Are there any fault codes or indicator lights showing?",
            field_key="fault_codes",
            input_type="text",
            placeholder="e.g. flashing red light, code E1, no lights at all",
        ),
        TriageFollowUpPrompt(
            question="When did the burner last work correctly?",
            field_key="last_working",
            input_type="buttons",
            options=["Today", "This week", "Over a week ago", "Never installed / new"],
        ),
    ],
    "B": [  # Burner Starts Then Locks Out
        TriageFollowUpPrompt(
            question="At what stage does the burner lock out?",
            field_key="lockout_stage",
            input_type="buttons",
            options=["During pre-purge", "At ignition", "After flame established", "Not sure"],
        ),
        TriageFollowUpPrompt(
            question="How long does the burner run before locking out?",
            field_key="run_duration",
            input_type="buttons",
            options=["Less than 10 seconds", "10-30 seconds", "1-5 minutes", "More than 5 minutes"],
        ),
        TriageFollowUpPrompt(
            question="Any fault codes displayed?",
            field_key="fault_codes",
            input_type="text",
            placeholder="e.g. lockout code, LED flashes",
        ),
    ],
    "C": [  # Burner Running Poorly
        TriageFollowUpPrompt(
            question="What symptoms are you experiencing?",
            field_key="symptoms",
            input_type="buttons",
            options=["Unusual noise", "Yellow/smoky flame", "Flame lifting off", "Pulsating/rumbling", "Other"],
        ),
        TriageFollowUpPrompt(
            question="Has anything changed recently (gas supply, controls, environment)?",
            field_key="recent_changes",
            input_type="text",
            placeholder="Describe any recent changes...",
        ),
    ],
    "D": [  # Installation / Commissioning
        TriageFollowUpPrompt(
            question="What stage are you at?",
            field_key="install_stage",
            input_type="buttons",
            options=["Pre-installation planning", "Mid-installation", "Commissioning", "Post-commissioning issue"],
        ),
        TriageFollowUpPrompt(
            question="Do you have the installation manual for this burner?",
            field_key="has_manual",
            input_type="buttons",
            options=["Yes", "No"],
        ),
    ],
    "E": [  # Documentation Request
        TriageFollowUpPrompt(
            question="What documentation do you need?",
            field_key="doc_type",
            input_type="buttons",
            options=["Installation manual", "Wiring diagram", "Gas train schematic", "Spare parts list", "Data sheet", "Other"],
        ),
    ],
    "F": [  # Spare Parts
        TriageFollowUpPrompt(
            question="Do you know the part number?",
            field_key="part_number",
            input_type="text",
            placeholder="e.g. FD-IGN-001 or describe the part",
        ),
        TriageFollowUpPrompt(
            question="Is this an urgent / breakdown situation?",
            field_key="urgency",
            input_type="buttons",
            options=["Yes - burner is down", "No - planned maintenance", "Stock order"],
        ),
    ],
    # G = "Something Else" — free text is captured in issue_free_text, no extra follow-ups
}