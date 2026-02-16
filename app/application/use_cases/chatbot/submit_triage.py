from datetime import datetime, timezone
from typing import Optional

from app.domain.entities.chat_triage import ChatTriage
from app.domain.entities.chat_session import ChatSession
from app.application.interfaces.repositories.chat_triage_repository import ChatTriageRepository
from app.application.interfaces.repositories.chat_session_repository import ChatSessionRepository
from app.application.dtos.triage_dtos import TriageSubmissionDTO, TriageResponseDTO


class SubmitTriage:
    """
    Use Case: Submit triage questionnaire and create/attach to a chat session
    
    Flow:
    1. Validate triage data
    2. Create a new chat session (or attach to existing)
    3. Save triage record linked to session
    4. Return triage summary + session_id for subsequent chat queries
    """
    
    def __init__(
        self,
        triage_repository: ChatTriageRepository,
        session_repository: ChatSessionRepository,
    ):
        self.triage_repository = triage_repository
        self.session_repository = session_repository
    
    async def execute(self, dto: TriageSubmissionDTO) -> TriageResponseDTO:
        """
        Process triage submission
        
        Args:
            dto: Completed triage questionnaire answers
            
        Returns:
            TriageResponseDTO with session_id ready for chat
            
        Raises:
            ValueError: If triage data is invalid or session already has triage
        """
        
        # Validation

        if dto.issue_category not in ChatTriage.ISSUE_CATEGORIES:
            raise ValueError(
                f"Invalid issue category: {dto.issue_category}. "
                f"Must be one of: {', '.join(ChatTriage.ISSUE_CATEGORIES.keys())}"
            )
        
        if dto.burner_series and dto.burner_series not in ChatTriage.BURNER_SERIES:
            raise ValueError(
                f"Invalid burner series: {dto.burner_series}. "
                f"Must be one of: {', '.join(ChatTriage.BURNER_SERIES)}"
            )
        
        if dto.has_serial_number and dto.serial_number:
            if not ChatTriage.validate_serial_number(dto.serial_number):
                raise ValueError(
                    "Invalid serial number format. Expected: letter followed by digits (e.g. J123456)"
                )
        
        # Session retrieval
        if dto.session_id:
            session = await self.session_repository.find_by_id(dto.session_id)
            if not session:
                raise ValueError(f"Chat session {dto.session_id} not found")
            
            # Check session doesn't already have triage
            existing = await self.triage_repository.find_by_session_id(dto.session_id)
            if existing:
                raise ValueError(
                    f"Session {dto.session_id} already has a triage record. "
                    "Create a new session for a new enquiry."
                )
        else:
            # Generate session title from triage context
            category_label = ChatTriage.ISSUE_CATEGORIES[dto.issue_category]
            series_label = f"{dto.burner_series} Series" if dto.burner_series else "Unknown Burner"
            title = f"{series_label} — {category_label}"
            
            session = ChatSession(
                id=None,
                user_id=dto.user_id,
                title=title,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session = await self.session_repository.create(session)
        
        # Build triage entity and save
        issue_category_label = ChatTriage.ISSUE_CATEGORIES[dto.issue_category]
        
        triage = ChatTriage(
            id=None,
            session_id=session.id,
            user_id=dto.user_id,
            burner_series=dto.burner_series,
            burner_identified_via=dto.burner_identified_via,
            serial_number=dto.serial_number if dto.has_serial_number else None,
            has_serial_number=dto.has_serial_number,
            issue_category=dto.issue_category,
            issue_category_label=issue_category_label,
            issue_free_text=dto.issue_free_text if dto.issue_category == "G" else None,
            follow_up_answers=dto.follow_up_answers,
            created_at=datetime.now(timezone.utc),
        )
        
        saved_triage = await self.triage_repository.save(triage)
        
        return TriageResponseDTO(
            triage_id=saved_triage.id,
            session_id=session.id,
            burner_series=saved_triage.burner_series,
            serial_number=saved_triage.serial_number,
            issue_category=saved_triage.issue_category,
            issue_category_label=issue_category_label,
            context_summary=saved_triage.get_context_summary(),
            created_at=saved_triage.created_at,
        )