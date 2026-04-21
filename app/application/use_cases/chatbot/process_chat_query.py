from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.domain.entities.chat_session import ChatSession
from ...interfaces.repositories.chat_repository import ChatRepository
from ...interfaces.repositories.chat_session_repository import ChatSessionRepository
from ...interfaces.repositories.chat_triage_repository import ChatTriageRepository
from ...interfaces.repositories.vector_store_repository import VectorStoreRepository
from ...interfaces.services.llm_service import LLMService
from ...dtos.chat_dtos import ChatQueryDTO, ChatResponseDTO
from ....domain.entities.chat_message import ChatMessage


class ProcessChatQuery:
    """
    Use Case: Process chat query using RAG
    
    Flow:
    1. Create or fetch chat session
    2. Load triage context (if available) for the session
    3. Generate embedding for query
    4. Retrieve similar documents (filtered by burner series if known)
    5. Generate response with context + triage background
    6. Save chat message linked to session
    """
    
    SIMILARITY_THRESHOLD = 0.3
    TOP_K = 5
    
    def __init__(
        self,
        chat_repository: ChatRepository,
        chat_session_repository: ChatSessionRepository,
        triage_repository: ChatTriageRepository,
        vector_store_repository: VectorStoreRepository,
        llm_service: LLMService
    ):
        self.chat_repository = chat_repository
        self.chat_session_repository = chat_session_repository
        self.triage_repository = triage_repository
        self.vector_store_repository = vector_store_repository
        self.llm_service = llm_service
    
    async def execute(
        self,
        dto: ChatQueryDTO,
        filters: Optional[Dict[str, Any]] = None
    ) -> ChatResponseDTO:
        """
        Process user query and generate response
        
        Args:
            dto: Chat query with user_id, query and optional session_id
            filters: Optional filters for retrieval
            
        Returns:
            ChatResponseDTO with response, sources and session_id
        """

        if dto.session_id:
            session = await self.chat_session_repository.find_by_id(dto.session_id)
            if not session:
                raise ValueError(f"Chat session {dto.session_id} not found")

            await self.chat_session_repository.update_title(
                session_id=session.id,
                title=session.title or ChatSession.generate_title_from_query(dto.query)
            )
        else:
            session = ChatSession(
                id=None,
                user_id=dto.user_id,
                title=ChatSession.generate_title_from_query(dto.query),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session = await self.chat_session_repository.create(session)
        
        # Load triage context if available
        triage_context = None
        triage = await self.triage_repository.find_by_session_id(session.id)
        if triage:
            triage_context = triage.get_context_summary()
            
            # Auto-apply burner series filter from triage
            if triage.burner_series and (filters is None or 'product_series' not in filters):
                filters = filters or {}
                filters['product_series'] = triage.burner_series
        
        # Generate embedding for query
        query_embedding = await self.llm_service.generate_embedding(dto.query)
        
        # Retrieve relevant documents
        retrieved_chunks = await self.vector_store_repository.similarity_search(
            query_embedding=query_embedding,
            k=self.TOP_K,
            filters=filters
        )
        
        # Filter by similarity threshold
        relevant_chunks = [
            chunk for chunk in retrieved_chunks
            if chunk['similarity_score'] >= self.SIMILARITY_THRESHOLD
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
                created_at=datetime.now(timezone.utc)
            )
            saved_message = await self.chat_repository.save(chat_message)

            return ChatResponseDTO(
                message_id=saved_message.id,
                session_id=session.id,
                query=dto.query,
                response=response_text,
                sources=[],
                created_at=datetime.now(timezone.utc)
            )
        
        # Extract context
        context_documents = [chunk['content'] for chunk in relevant_chunks]
        
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
            query=enriched_query,
            context_documents=context_documents
        )
        
        chat_message = ChatMessage(
            id=None,
            user_id=dto.user_id,
            session_id=session.id,
            query=dto.query,
            response=response,
            source_document_ids=[chunk['id'] for chunk in relevant_chunks],
            created_at=datetime.now(timezone.utc)
        )
        
        saved_message = await self.chat_repository.save(chat_message)
        
        sources = [
            {
                'document_id': chunk['document_id'],
                'content': chunk['content'],
                'similarity_score': chunk['similarity_score'],
                'metadata': chunk['metadata']
            }
            for chunk in relevant_chunks
        ]
        
        return ChatResponseDTO(
            message_id=saved_message.id,
            session_id=session.id,
            query=dto.query,
            response=response,
            sources=sources,
            created_at=saved_message.created_at
        )