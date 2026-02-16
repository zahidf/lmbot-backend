from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class TriageSubmissionRequest(BaseModel):
    """Request to submit completed triage questionnaire"""
    
    session_id: Optional[str] = None  # None = create new session
    
    # Q1: Burner identification
    burner_series: Optional[str] = Field(
        None,
        description="Burner series: FD, TX, DB, FDB or null if unknown"
    )
    burner_identified_via: str = Field(
        "direct_selection",
        description="How burner was identified: direct_selection | image_identification | unknown"
    )
    
    # Q2: Serial number
    serial_number: Optional[str] = Field(
        None,
        description="Burner serial number, e.g. J123456"
    )
    has_serial_number: bool = Field(
        False,
        description="Whether the user has a serial number"
    )
    
    # Q3: Issue category
    issue_category: str = Field(
        ...,
        description="Issue category code: A-G"
    )
    issue_free_text: Optional[str] = Field(
        None,
        description="Free text description (used when issue_category is G)"
    )
    
    # Q4: Follow-up answers
    follow_up_answers: Dict[str, Any] = Field(
        default_factory=dict,
        description="Answers to category-specific follow-up questions"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "burner_series": "TX",
                "burner_identified_via": "direct_selection",
                "serial_number": "J123456",
                "has_serial_number": True,
                "issue_category": "A",
                "follow_up_answers": {
                    "has_power": "Yes",
                    "fault_codes": "Flashing red light",
                    "last_working": "This week"
                }
            }
        }
    )


class TriageResponse(BaseModel):
    """Response after triage submission"""
    triage_id: str
    session_id: str
    burner_series: Optional[str]
    serial_number: Optional[str]
    issue_category: str
    issue_category_label: str
    context_summary: str
    created_at: datetime


class FollowUpPromptResponse(BaseModel):
    """A single follow-up question"""
    question: str
    field_key: str
    input_type: str
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None


class TriageFollowUpsResponse(BaseModel):
    """Follow-up prompts for a given issue category"""
    category: str
    category_label: str
    follow_ups: List[FollowUpPromptResponse]


class TriageConfigResponse(BaseModel):
    """Full triage configuration for frontend rendering"""
    burner_series: List[str]
    issue_categories: Dict[str, str]
    serial_number_example: str
    serial_number_tooltip: str