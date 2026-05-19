from fastapi import APIRouter, Depends, HTTPException, status
import logging

from ..schemas.ticket_schemas import (
    TicketResponse,
    TicketDetailResponse,
    TicketActivityResponse,
    TicketListResponse,
)
from ..dependencies import (
    get_current_user,
    get_ticket_repository,
    get_ticket_activity_repository,
    get_escalate_ticket_use_case,
)
from ....application.use_cases.tickets.escalate_ticket import EscalateTicket
from ....application.dtos.ticket_dtos import EscalateTicketDTO
from ....infrastructure.persistence.repositories.ticket_repository_impl import TicketRepositoryImpl
from ....infrastructure.persistence.repositories.ticket_activity_repository_impl import TicketActivityRepositoryImpl

router = APIRouter(prefix="/tickets", tags=["tickets"])
logger = logging.getLogger(__name__)


def _ticket_response(ticket) -> TicketResponse:
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        session_id=ticket.session_id,
        summary=ticket.summary,
        status=ticket.status,
        assigned_to=ticket.assigned_to,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    limit: int = 20,
    offset: int = 0,
    current_user=Depends(get_current_user),
    ticket_repo: TicketRepositoryImpl = Depends(get_ticket_repository),
):
    """List all tickets for the current user, ordered by most recent."""
    if limit > 100:
        limit = 100

    tickets = await ticket_repo.find_by_user_id(
        user_id=current_user["id"],
        limit=limit,
        offset=offset,
    )

    return TicketListResponse(
        tickets=[
            TicketResponse(
                ticket_id=t.id,
                session_id=t.session_id,
                summary=t.summary,
                status=t.status,
                assigned_to=t.assigned_to,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tickets
        ],
        total=len(tickets),
    )


@router.get("/session/{session_id}", response_model=TicketDetailResponse)
async def get_ticket_by_session(
    session_id: str,
    current_user=Depends(get_current_user),
    ticket_repo: TicketRepositoryImpl = Depends(get_ticket_repository),
    activity_repo: TicketActivityRepositoryImpl = Depends(get_ticket_activity_repository),
):
    """Get the ticket associated with a chat session."""
    ticket = await ticket_repo.find_by_session_id(session_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    if ticket.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    activities = await activity_repo.find_by_ticket_id(ticket.id)

    return TicketDetailResponse(
        ticket_id=ticket.id,
        session_id=ticket.session_id,
        summary=ticket.summary,
        status=ticket.status,
        assigned_to=ticket.assigned_to,
        activities=[
            TicketActivityResponse(
                id=a.id,
                action=a.action,
                actor=a.actor,
                note=a.note,
                created_at=a.created_at,
            )
            for a in activities
        ],
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: str,
    current_user=Depends(get_current_user),
    ticket_repo: TicketRepositoryImpl = Depends(get_ticket_repository),
    activity_repo: TicketActivityRepositoryImpl = Depends(get_ticket_activity_repository),
):
    """Get a ticket with its full activity timeline."""
    ticket = await ticket_repo.find_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    if ticket.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    activities = await activity_repo.find_by_ticket_id(ticket_id)

    return TicketDetailResponse(
        ticket_id=ticket.id,
        session_id=ticket.session_id,
        summary=ticket.summary,
        status=ticket.status,
        assigned_to=ticket.assigned_to,
        activities=[
            TicketActivityResponse(
                id=a.id,
                action=a.action,
                actor=a.actor,
                note=a.note,
                created_at=a.created_at,
            )
            for a in activities
        ],
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.post("/{ticket_id}/escalate", response_model=TicketDetailResponse)
async def escalate_ticket(
    ticket_id: str,
    current_user=Depends(get_current_user),
    use_case: EscalateTicket = Depends(get_escalate_ticket_use_case),
    activity_repo: TicketActivityRepositoryImpl = Depends(get_ticket_activity_repository),
):
    """
    Escalate an open ticket to the technical team.

    Generates an LLM summary of the chat session and reassigns the ticket.
    Only available when the ticket is in 'open' status.
    """
    try:
        dto = EscalateTicketDTO(ticket_id=ticket_id, user_id=current_user["id"])
        result = await use_case.execute(dto)

        activities = await activity_repo.find_by_ticket_id(ticket_id)

        return TicketDetailResponse(
            ticket_id=result.ticket_id,
            session_id=result.session_id,
            summary=result.summary,
            status=result.status,
            assigned_to=result.assigned_to,
            activities=[
                TicketActivityResponse(
                    id=a.id,
                    action=a.action,
                    actor=a.actor,
                    note=a.note,
                    created_at=a.created_at,
                )
                for a in activities
            ],
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Escalate ticket failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to escalate ticket: {str(e)}",
        )
