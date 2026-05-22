import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Optional, Dict, Any

logger = logging.getLogger(__name__)

from app.domain.entities.chat_session import ChatSession
from app.domain.entities.ticket import Ticket
from app.domain.entities.ticket_activity import TicketActivity
from ...interfaces.repositories.chat_repository import ChatRepository
from ...interfaces.repositories.chat_session_repository import ChatSessionRepository
from ...interfaces.repositories.chat_triage_repository import ChatTriageRepository
from ...interfaces.repositories.vector_store_repository import VectorStoreRepository
from ...interfaces.repositories.ticket_repository import TicketRepository
from ...interfaces.repositories.ticket_activity_repository import (
    TicketActivityRepository,
)
from ...interfaces.services.llm_service import LLMService
from ...dtos.chat_dtos import ChatQueryDTO, ChatResponseDTO
from ....domain.entities.chat_message import ChatMessage


class ProcessChatQuery:
    """
    Use Case: Process chat query using RAG

    Flow:
    1. Create or fetch chat session (new sessions get a ticket assigned to lmbot)
    2. Load triage context (if available) for the session
    3. Generate embedding for query
    4. Retrieve similar documents (filtered by burner series if known)
    5. Generate response with context + triage background
    6. Detect whether the bot could answer; set can_escalate accordingly
    7. Save chat message linked to session
    """

    SIMILARITY_THRESHOLD = 0.3
    TOP_K = 2

    # Phrases that indicate the LLM could not form an answer from the retrieved chunks
    _CANNOT_ANSWER_PHRASES = [
        "cannot answer",
        "can't answer",
        "don't have enough information",
        "do not have enough information",
        "unable to answer",
        "not enough information",
        "no relevant information",
        "no information available",
    ]

    def __init__(
        self,
        chat_repository: ChatRepository,
        chat_session_repository: ChatSessionRepository,
        triage_repository: ChatTriageRepository,
        vector_store_repository: VectorStoreRepository,
        llm_service: LLMService,
        ticket_repository: TicketRepository,
        ticket_activity_repository: TicketActivityRepository,
    ):
        self.chat_repository = chat_repository
        self.chat_session_repository = chat_session_repository
        self.triage_repository = triage_repository
        self.vector_store_repository = vector_store_repository
        self.llm_service = llm_service
        self.ticket_repository = ticket_repository
        self.ticket_activity_repository = ticket_activity_repository

    @staticmethod
    def _cannot_answer(response: str) -> bool:
        lower = response.lower()
        return any(
            phrase in lower for phrase in ProcessChatQuery._CANNOT_ANSWER_PHRASES
        )

    async def _create_ticket_for_session(self, session_id: str, user_id: str) -> Ticket:
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id=None,
            session_id=session_id,
            user_id=user_id,
            summary=None,
            status="open",
            assigned_to="lmbot",
            created_at=now,
            updated_at=now,
        )
        ticket = await self.ticket_repository.save(ticket)

        activity = TicketActivity(
            id=None,
            ticket_id=ticket.id,
            action="created",
            actor="lmbot",
            note=None,
            created_at=now,
        )
        await self.ticket_activity_repository.save(activity)
        return ticket

    async def execute(
        self, dto: ChatQueryDTO, filters: Optional[Dict[str, Any]] = None
    ) -> ChatResponseDTO:

        is_new_session = not dto.session_id

        if dto.session_id:
            session = await self.chat_session_repository.find_by_id(dto.session_id)
            if not session:
                raise ValueError(f"Chat session {dto.session_id} not found")

            ticket = await self.ticket_repository.find_by_session_id(session.id)
            if ticket and ticket.status == "escalated":
                raise ValueError(
                    "This session has been escalated to the technical team "
                    "and is no longer accepting messages."
                )

            await self.chat_session_repository.update_title(
                session_id=session.id,
                title=session.title or ChatSession.generate_title_from_query(dto.query),
            )
        else:
            session = ChatSession(
                id=None,
                user_id=dto.user_id,
                title=ChatSession.generate_title_from_query(dto.query),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session = await self.chat_session_repository.create(session)

        if is_new_session:
            await self._create_ticket_for_session(session.id, dto.user_id)

        # Load triage context if available
        triage_context = None
        triage = await self.triage_repository.find_by_session_id(session.id)
        if triage:
            triage_context = triage.get_context_summary()

            # Auto-apply burner series filter from triage
            if triage.burner_series and (
                filters is None or "product_series" not in filters
            ):
                filters = filters or {}
                filters["product_series"] = triage.burner_series

        # Generate embedding for query
        query_embedding = await self.llm_service.generate_embedding(dto.query)

        # Retrieve relevant documents
        retrieved_chunks = await self.vector_store_repository.similarity_search(
            query_embedding=query_embedding, k=self.TOP_K, filters=filters
        )

        # Filter by similarity threshold
        relevant_chunks = [
            chunk
            for chunk in retrieved_chunks
            if chunk["similarity_score"] >= self.SIMILARITY_THRESHOLD
        ]

        if not relevant_chunks:
            response_text = (
                "I couldn't find relevant information in the documentation "
                "to answer your question. Please try rephrasing or contact "
                "the Technical Team directly."
            )

            chat_message = ChatMessage(
                id=None,
                user_id=dto.user_id,
                session_id=session.id,
                query=dto.query,
                response=response_text,
                source_document_ids=[],
                created_at=datetime.now(timezone.utc),
            )
            saved_message = await self.chat_repository.save(chat_message)

            ticket = await self.ticket_repository.find_by_session_id(session.id)

            return ChatResponseDTO(
                message_id=saved_message.id,
                session_id=session.id,
                query=dto.query,
                response=response_text,
                sources=[],
                created_at=datetime.now(timezone.utc),
                can_escalate=True,
                ticket_id=ticket.id if ticket else None,
            )

        # Extract context
        context_documents = [chunk["content"] for chunk in relevant_chunks]

        # Build query with triage context
        enriched_query = dto.query
        if triage_context:
            enriched_query = (
                f"[Customer Background from Triage]\n"
                f"{triage_context}\n\n"
                f"[Customer Question]\n"
                f"{dto.query}"
            )

        response = await self.llm_service.generate_response(
            query=enriched_query, context_documents=context_documents
        )

        # Detect whether LLM acknowledged it could not answer despite having chunks
        can_escalate = self._cannot_answer(response)

        ticket_id = None
        if can_escalate:
            ticket = await self.ticket_repository.find_by_session_id(session.id)
            ticket_id = ticket.id if ticket else None

        chat_message = ChatMessage(
            id=None,
            user_id=dto.user_id,
            session_id=session.id,
            query=dto.query,
            response=response,
            source_document_ids=[chunk["id"] for chunk in relevant_chunks],
            created_at=datetime.now(timezone.utc),
        )

        saved_message = await self.chat_repository.save(chat_message)

        sources = [
            {
                "document_id": chunk["document_id"],
                "content": chunk["content"],
                "similarity_score": chunk["similarity_score"],
                "metadata": chunk["metadata"],
            }
            for chunk in relevant_chunks
        ]

        return ChatResponseDTO(
            message_id=saved_message.id,
            session_id=session.id,
            query=dto.query,
            response=response,
            sources=sources,
            created_at=saved_message.created_at,
            can_escalate=can_escalate,
            ticket_id=ticket_id,
        )

    async def stream(
        self, dto: ChatQueryDTO, filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Stream a chat response as SSE events.

        Event types:
          metadata — sent before LLM tokens; carries session_id
          token    — one LLM token
          done     — final event; carries message_id, sources, can_escalate, ticket_id
          error    — sent on failure
        """
        try:
            is_new_session = not dto.session_id

            if dto.session_id:
                session = await self.chat_session_repository.find_by_id(dto.session_id)
                if not session:
                    raise ValueError(f"Chat session {dto.session_id} not found")
                ticket = await self.ticket_repository.find_by_session_id(session.id)
                if ticket and ticket.status == "escalated":
                    raise ValueError(
                        "This session has been escalated to the technical team "
                        "and is no longer accepting messages."
                    )
                await self.chat_session_repository.update_title(
                    session_id=session.id,
                    title=session.title
                    or ChatSession.generate_title_from_query(dto.query),
                )
            else:
                session = ChatSession(
                    id=None,
                    user_id=dto.user_id,
                    title=ChatSession.generate_title_from_query(dto.query),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session = await self.chat_session_repository.create(session)

            if is_new_session:
                await self._create_ticket_for_session(session.id, dto.user_id)

            triage_context = None
            triage = await self.triage_repository.find_by_session_id(session.id)
            if triage:
                triage_context = triage.get_context_summary()
                if triage.burner_series and (
                    filters is None or "product_series" not in filters
                ):
                    filters = filters or {}
                    filters["product_series"] = triage.burner_series

            query_embedding = await self.llm_service.generate_embedding(dto.query)
            retrieved_chunks = await self.vector_store_repository.similarity_search(
                query_embedding=query_embedding, k=self.TOP_K, filters=filters
            )
            relevant_chunks = [
                c
                for c in retrieved_chunks
                if c["similarity_score"] >= self.SIMILARITY_THRESHOLD
            ]

            yield f"data: {json.dumps({'type': 'metadata', 'session_id': str(session.id)})}\n\n"

            if not relevant_chunks:
                response_text = (
                    "I couldn't find relevant information in the documentation "
                    "to answer your question. Please try rephrasing or contact "
                    "the Technical Team directly."
                )
                chat_message = ChatMessage(
                    id=None,
                    user_id=dto.user_id,
                    session_id=session.id,
                    query=dto.query,
                    response=response_text,
                    source_document_ids=[],
                    created_at=datetime.now(timezone.utc),
                )
                saved_message = await self.chat_repository.save(chat_message)
                ticket = await self.ticket_repository.find_by_session_id(session.id)
                yield f"data: {json.dumps({'type': 'done', 'message_id': str(saved_message.id), 'sources': [], 'can_escalate': True, 'ticket_id': str(ticket.id) if ticket else None, 'response': response_text})}\n\n"
                return

            context_documents = [chunk["content"] for chunk in relevant_chunks]
            enriched_query = dto.query
            if triage_context:
                enriched_query = (
                    f"[Customer Background from Triage]\n"
                    f"{triage_context}\n\n"
                    f"[Customer Question]\n"
                    f"{dto.query}"
                )

            full_response = []
            async for token in self.llm_service.stream_response(
                enriched_query, context_documents
            ):
                full_response.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            response_text = "".join(full_response)
            can_escalate = self._cannot_answer(response_text)

            ticket_id = None
            if can_escalate:
                ticket = await self.ticket_repository.find_by_session_id(session.id)
                ticket_id = str(ticket.id) if ticket else None

            chat_message = ChatMessage(
                id=None,
                user_id=dto.user_id,
                session_id=session.id,
                query=dto.query,
                response=response_text,
                source_document_ids=[chunk["id"] for chunk in relevant_chunks],
                created_at=datetime.now(timezone.utc),
            )
            saved_message = await self.chat_repository.save(chat_message)

            sources = [
                {
                    "document_id": chunk["document_id"],
                    "content": chunk["content"],
                    "similarity_score": chunk["similarity_score"],
                    "metadata": chunk["metadata"],
                }
                for chunk in relevant_chunks
            ]

            yield f"data: {json.dumps({'type': 'done', 'message_id': str(saved_message.id), 'sources': sources, 'can_escalate': can_escalate, 'ticket_id': ticket_id})}\n\n"

        except ValueError as e:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"
        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'detail': 'An error occurred while processing your query'})}\n\n"
