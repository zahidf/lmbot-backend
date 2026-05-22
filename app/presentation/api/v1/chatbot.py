import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List
from ..schemas.chat_schemas import (
    ChatQueryRequest,
    ChatResponse,
    ChatSourceResponse,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionUpdateRequest,
    ChatHistoryResponse,
    SessionLoadResponse,
)
from ..schemas.triage_schemas import TriageResponse, TriageConfigResponse
from ..schemas.ticket_schemas import TicketDetailResponse, TicketActivityResponse
from ..dependencies import (
    get_current_user,
    get_process_chat_query_use_case,
    get_chat_repository,
    get_chat_session_repository,
    get_vector_store_repository,
    get_load_session_context_use_case,
)
from ....infrastructure.persistence.repositories.langchain_vector_store_repository import (
    LangChainVectorStoreRepository,
)
from ....application.use_cases.chatbot.process_chat_query import ProcessChatQuery
from ....application.use_cases.chatbot.load_session_context import LoadSessionContext
from ....application.dtos.chat_dtos import ChatQueryDTO
from ....application.interfaces.repositories.chat_repository import ChatRepository
from ....infrastructure.persistence.repositories.chat_session_repository_impl import (
    ChatSessionRepositoryImpl,
)
import logging

router = APIRouter(prefix="/chat", tags=["chatbot"])
logger = logging.getLogger(__name__)


# ─── Chat Query ───────────────────────────────────────────────


@router.post("/query", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat_query(
    request: ChatQueryRequest,
    current_user=Depends(get_current_user),
    use_case: ProcessChatQuery = Depends(get_process_chat_query_use_case),
):
    """
    Process a chat query using RAG.

    - **query**: User's question (1-2000 characters)
    - **session_id**: Optional session ID. If omitted, a new chat session is created.

    Returns:
    - Generated response with source citations and session_id
    """
    try:
        dto = ChatQueryDTO(
            user_id=current_user["id"],
            query=request.query,
            session_id=request.session_id,
        )

        result = await use_case.execute(dto)
        return ChatResponse(
            message_id=result.message_id,
            session_id=result.session_id,
            query=result.query,
            response=result.response,
            sources=[ChatSourceResponse(**source) for source in result.sources],
            created_at=result.created_at,
            can_escalate=result.can_escalate,
            ticket_id=result.ticket_id,
        )

    except ValueError as e:
        msg = str(e)
        http_status = (
            status.HTTP_400_BAD_REQUEST
            if "escalated" in msg
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=http_status, detail=msg)
    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your query: {str(e)}",
        )


# ─── Chat Query (Streaming) ──────────────────────────────────


@router.post("/query/stream")
async def stream_chat_query(
    request: ChatQueryRequest,
    current_user=Depends(get_current_user),
    use_case: ProcessChatQuery = Depends(get_process_chat_query_use_case),
):
    """
    Stream a chat response as Server-Sent Events.

    Events:
    - `metadata` — sent once before tokens; contains `session_id`
    - `token`    — one LLM token; contains `content`
    - `done`     — final event; contains `message_id`, `sources`, `can_escalate`, `ticket_id`
    - `error`    — sent on failure; contains `detail`
    """
    dto = ChatQueryDTO(
        user_id=current_user["id"], query=request.query, session_id=request.session_id
    )
    return StreamingResponse(
        use_case.stream(dto),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Chat Sessions ───────────────────────────────────────────


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    limit: int = 20,
    offset: int = 0,
    current_user=Depends(get_current_user),
    session_repo: ChatSessionRepositoryImpl = Depends(get_chat_session_repository),
):
    """
    List all chat sessions for the current user.

    - **limit**: Max sessions to return (default: 20, max: 100)
    - **offset**: Pagination offset

    Returns sessions ordered by most recently updated.
    """
    try:
        if limit > 100:
            limit = 100

        sessions = await session_repo.find_by_user_id(
            user_id=current_user["id"], limit=limit, offset=offset
        )

        return ChatSessionListResponse(
            sessions=[
                ChatSessionResponse(
                    id=s.id,
                    title=s.title,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
                for s in sessions
            ],
            total=len(sessions),
        )
    except Exception as e:
        logger.error(f"List sessions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat sessions: {str(e)}",
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_chat_session(
    session_id: str,
    current_user=Depends(get_current_user),
    session_repo: ChatSessionRepositoryImpl = Depends(get_chat_session_repository),
    chat_repo: ChatRepository = Depends(get_chat_repository),
    vector_repo: LangChainVectorStoreRepository = Depends(get_vector_store_repository),
):
    """
    Get a chat session with all its messages.

    - **session_id**: UUID of the chat session
    """
    try:
        session = await session_repo.find_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        # Verify ownership
        if session.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        # Get messages for this session
        messages = await chat_repo.find_by_session_id(session_id)

        # Collect all chunk IDs across all messages and fetch in one query
        all_chunk_ids = [
            cid for msg in messages for cid in (msg.source_document_ids or [])
        ]
        chunks_by_id = {}
        if all_chunk_ids:
            chunks = await vector_repo.get_chunks_by_ids(all_chunk_ids)
            chunks_by_id = {chunk["id"]: chunk for chunk in chunks}

        return ChatSessionDetailResponse(
            id=session.id,
            title=session.title,
            messages=[
                ChatResponse(
                    message_id=msg.id,
                    session_id=msg.session_id,
                    query=msg.query,
                    response=msg.response,
                    sources=[
                        ChatSourceResponse(
                            document_id=chunks_by_id[cid]["document_id"],
                            content=chunks_by_id[cid]["content"],
                            similarity_score=0.0,
                            metadata=chunks_by_id[cid]["metadata"],
                        )
                        for cid in (msg.source_document_ids or [])
                        if cid in chunks_by_id
                    ],
                    created_at=msg.created_at,
                )
                for msg in messages
            ],
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat session: {str(e)}",
        )


@router.get("/sessions/{session_id}/load", response_model=SessionLoadResponse)
async def load_session_context(
    session_id: str,
    current_user=Depends(get_current_user),
    use_case: LoadSessionContext = Depends(get_load_session_context_use_case),
):
    """
    Load all session context in a single request.

    Returns the session, messages (with sources), triage data, triage config,
    and ticket status
    """
    try:
        result = await use_case.execute(
            session_id=session_id,
            user_id=current_user["id"],
        )

        triage_response = None
        triage_config_response = None
        if result.triage:
            triage_response = TriageResponse(
                triage_id=result.triage.triage_id,
                session_id=result.triage.session_id,
                burner_series=result.triage.burner_series,
                serial_number=result.triage.serial_number,
                issue_category=result.triage.issue_category,
                issue_category_label=result.triage.issue_category_label,
                context_summary=result.triage.context_summary,
                created_at=result.triage.created_at,
            )
            triage_config_response = TriageConfigResponse(
                burner_series=result.triage_config["burner_series"],
                issue_categories=result.triage_config["issue_categories"],
                serial_number_example=result.triage_config["serial_number_example"],
                serial_number_tooltip=result.triage_config["serial_number_tooltip"],
            )

        ticket_response = None
        if result.ticket:
            ticket_response = TicketDetailResponse(
                ticket_id=result.ticket.ticket_id,
                session_id=result.ticket.session_id,
                summary=result.ticket.summary,
                status=result.ticket.status,
                assigned_to=result.ticket.assigned_to,
                activities=[
                    TicketActivityResponse(
                        id=a.id,
                        action=a.action,
                        actor=a.actor,
                        note=a.note,
                        created_at=a.created_at,
                    )
                    for a in result.ticket.activities
                ],
                created_at=result.ticket.created_at,
                updated_at=result.ticket.updated_at,
            )

        return SessionLoadResponse(
            session=ChatSessionResponse(
                id=result.session_id,
                title=result.session_title,
                created_at=result.session_created_at,
                updated_at=result.session_updated_at,
            ),
            messages=[
                ChatResponse(
                    message_id=msg.message_id,
                    session_id=msg.session_id,
                    query=msg.query,
                    response=msg.response,
                    sources=[ChatSourceResponse(**s) for s in msg.sources],
                    created_at=msg.created_at,
                )
                for msg in result.messages
            ],
            triage=triage_response,
            triage_config=triage_config_response,
            ticket=ticket_response,
        )

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Load session context failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load session context: {str(e)}",
        )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    request: ChatSessionUpdateRequest,
    current_user=Depends(get_current_user),
    session_repo: ChatSessionRepositoryImpl = Depends(get_chat_session_repository),
):
    """
    Update a chat session title.

    - **session_id**: UUID of the chat session
    - **title**: New title for the session
    """
    try:
        # Verify session exists and belongs to user
        session = await session_repo.find_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        if session.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        updated = await session_repo.update_title(session_id, request.title)

        return ChatSessionResponse(
            id=updated.id,
            title=updated.title,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat session: {str(e)}",
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def delete_chat_session(
    session_id: str,
    current_user=Depends(get_current_user),
    session_repo: ChatSessionRepositoryImpl = Depends(get_chat_session_repository),
):
    """
    Delete a chat session and all its messages.

    - **session_id**: UUID of the chat session
    """
    try:
        # Verify ownership
        session = await session_repo.find_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        if session.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        deleted = await session_repo.delete(session_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
            )

        return {"message": "Chat session deleted successfully", "id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat session: {str(e)}",
        )


# ─── Legacy: Chat History (all messages for user) ────────────


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = 10,
    current_user=Depends(get_current_user),
    chat_repository: ChatRepository = Depends(get_chat_repository),
    vector_repo: LangChainVectorStoreRepository = Depends(get_vector_store_repository),
):
    """
    Get recent chat history for current user (across all sessions).

    - **limit**: Number of messages to retrieve (default: 10, max: 50)
    """
    try:
        if limit > 50:
            limit = 50

        messages = await chat_repository.find_by_user_id(
            user_id=current_user["id"], limit=limit
        )

        all_chunk_ids = [
            cid for msg in messages for cid in (msg.source_document_ids or [])
        ]
        chunks_by_id = {}
        if all_chunk_ids:
            chunks = await vector_repo.get_chunks_by_ids(all_chunk_ids)
            chunks_by_id = {chunk["id"]: chunk for chunk in chunks}

        return ChatHistoryResponse(
            messages=[
                ChatResponse(
                    message_id=msg.id,
                    session_id=msg.session_id,
                    query=msg.query,
                    response=msg.response,
                    sources=[
                        ChatSourceResponse(
                            document_id=chunks_by_id[cid]["document_id"],
                            content=chunks_by_id[cid]["content"],
                            similarity_score=0.0,
                            metadata=chunks_by_id[cid]["metadata"],
                        )
                        for cid in (msg.source_document_ids or [])
                        if cid in chunks_by_id
                    ],
                    created_at=msg.created_at,
                )
                for msg in messages
            ]
        )
    except Exception as e:
        logger.error(f"Get history failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {str(e)}",
        )
