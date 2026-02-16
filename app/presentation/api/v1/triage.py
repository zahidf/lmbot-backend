from fastapi import APIRouter, Depends, HTTPException, status
from ..schemas.triage_schemas import (
    TriageSubmissionRequest,
    TriageResponse,
    TriageFollowUpsResponse,
    FollowUpPromptResponse,
    TriageConfigResponse,
)
from ..dependencies import (
    get_current_user,
    get_submit_triage_use_case,
    get_chat_triage_repository,
)
from ....application.use_cases.chatbot.submit_triage import SubmitTriage
from ....application.dtos.triage_dtos import TriageSubmissionDTO, CATEGORY_FOLLOW_UPS
from ....application.interfaces.repositories.chat_triage_repository import ChatTriageRepository
from ....domain.entities.chat_triage import ChatTriage
import logging

router = APIRouter(prefix="/chat/triage", tags=["triage"])
logger = logging.getLogger(__name__)


# ─── Triage Config (for frontend rendering) ──────────────────

@router.get("/config", response_model=TriageConfigResponse)
async def get_triage_config():
    """
    Get triage questionnaire configuration.
    
    Returns burner series, issue categories, and serial number hints
    so the frontend can render the triage wizard.
    """
    return TriageConfigResponse(

        # currently these are constants, in the future, this data will be taken from database
        burner_series=ChatTriage.BURNER_SERIES,
        issue_categories=ChatTriage.ISSUE_CATEGORIES,
        serial_number_example="J123456",
        serial_number_tooltip=(
            "Usually found on the burner rating plate "
            "or inside the gas valve control panel."
        ),
    )


# ─── Follow-up prompts per category ──────────────────────────

@router.get("/follow-ups/{category}", response_model=TriageFollowUpsResponse)
async def get_follow_up_prompts(category: str):
    """
    Get the follow-up questions for a specific issue category.
    
    - **category**: Issue category code (A-G)
    
    Returns tailored follow-up prompts for the selected category.
    """
    # currently these are constants, in the future, this data will be taken from database

    if category not in ChatTriage.ISSUE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}. Must be one of: {', '.join(ChatTriage.ISSUE_CATEGORIES.keys())}",
        )
    
    prompts = CATEGORY_FOLLOW_UPS.get(category, [])
    
    return TriageFollowUpsResponse(
        category=category,
        category_label=ChatTriage.ISSUE_CATEGORIES[category],
        follow_ups=[
            FollowUpPromptResponse(
                question=p.question,
                field_key=p.field_key,
                input_type=p.input_type,
                options=p.options,
                placeholder=p.placeholder,
            )
            for p in prompts
        ],
    )


# ─── Submit triage ────────────────────────────────────────────

@router.post("/submit", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
async def submit_triage(
    request: TriageSubmissionRequest,
    current_user=Depends(get_current_user),
    use_case: SubmitTriage = Depends(get_submit_triage_use_case),
):
    """
    Submit completed triage questionnaire.
    
    Creates a new chat session (or attaches to an existing one)
    and saves the triage data. Returns a session_id that must be
    used for all subsequent /chat/query requests.
    
    Flow:
    1. Validates all triage inputs
    2. Creates chat session with descriptive title
    3. Persists triage record
    4. Returns session_id + context summary
    """
    try:
        dto = TriageSubmissionDTO(
            user_id=current_user["id"],
            session_id=request.session_id,
            burner_series=request.burner_series,
            burner_identified_via=request.burner_identified_via,
            serial_number=request.serial_number,
            has_serial_number=request.has_serial_number,
            issue_category=request.issue_category,
            issue_free_text=request.issue_free_text,
            follow_up_answers=request.follow_up_answers,
        )
        
        result = await use_case.execute(dto)
        
        return TriageResponse(
            triage_id=result.triage_id,
            session_id=result.session_id,
            burner_series=result.burner_series,
            serial_number=result.serial_number,
            issue_category=result.issue_category,
            issue_category_label=result.issue_category_label,
            context_summary=result.context_summary,
            created_at=result.created_at,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Triage submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit triage: {str(e)}",
        )


# ─── Get triage for a session ────────────────────────────────

@router.get("/session/{session_id}", response_model=TriageResponse)
async def get_session_triage(
    session_id: str,
    current_user=Depends(get_current_user),
    triage_repo: ChatTriageRepository = Depends(get_chat_triage_repository),
):
    """
    Get the triage record for a specific chat session.
    
    - **session_id**: UUID of the chat session
    """
    try:
        triage = await triage_repo.find_by_session_id(session_id)
        if not triage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No triage found for this session",
            )
        
        # Verify ownership
        if triage.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        return TriageResponse(
            triage_id=triage.id,
            session_id=triage.session_id,
            burner_series=triage.burner_series,
            serial_number=triage.serial_number,
            issue_category=triage.issue_category,
            issue_category_label=triage.issue_category_label or "",
            context_summary=triage.get_context_summary(),
            created_at=triage.created_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get triage failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve triage: {str(e)}",
        )