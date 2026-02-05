from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ...interfaces.repositories.chat_repository import ChatRepository
from ...interfaces.repositories.vector_store_repository import VectorStoreRepository
from ...interfaces.services.llm_service import LLMService
from ...dtos.chat_dtos import ChatQueryDTO, ChatResponseDTO
from ....domain.entities.chat_message import ChatMessage


class ProcessChatQuery:
    """
    Use Case: Process chat query using RAG
    
    Flow:
    1. Generate embedding for query
    2. Retrieve similar documents
    3. Generate response with context
    4. Save chat message
    """
    
    SIMILARITY_THRESHOLD = 0.3
    TOP_K = 5
    
    def __init__(
        self,
        chat_repository: ChatRepository,
        vector_store_repository: VectorStoreRepository,
        llm_service: LLMService
    ):
        self.chat_repository = chat_repository
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
            dto: Chat query with user_id and query
            filters: Optional filters for retrieval
            
        Returns:
            ChatResponseDTO with response and sources
        """
        
        #Generate embedding for query
        query_embedding = await self.llm_service.generate_embedding(dto.query)
        
        #Retrieve relevant documents
        retrieved_chunks = await self.vector_store_repository.similarity_search(
            query_embedding=query_embedding,
            k=self.TOP_K,
            filters=filters
        )
        
        #Filter by similarity threshold
        relevant_chunks = [
            chunk for chunk in retrieved_chunks
            if chunk['similarity_score'] >= self.SIMILARITY_THRESHOLD
        ]
        
        #Handle no relevant documents
        if not relevant_chunks:
            response_text = (
                "I couldn't find relevant information in the documentation "
                "to answer your question. Please try rephrasing or contact "
                "the Technical Team directly."
            )
            return ChatResponseDTO(
                message_id=None,
                query=dto.query,
                response=response_text,
                sources=[],
                created_at=datetime.now(timezone.utc)
            )
        
        #Extract context for LLM
        context_documents = [chunk['content'] for chunk in relevant_chunks]
        
        #Generate response
        response = await self.llm_service.generate_response(
            query=dto.query,
            context_documents=context_documents
        )
        
        #Create and save chat message
        chat_message = ChatMessage(
            id=None,
            user_id=dto.user_id,
            query=dto.query,
            response=response,
            source_document_ids=[chunk['document_id'] for chunk in relevant_chunks],
            created_at=datetime.now(timezone.utc)
        )
        
        saved_message = await self.chat_repository.save(chat_message)
        
        #Format sources
        sources = [
            {
                'document_id': chunk['document_id'],
                'content': chunk['content'][:200] + "...",
                'similarity_score': chunk['similarity_score'],
                'metadata': chunk['metadata']
            }
            for chunk in relevant_chunks
        ]
        
        #Return response
        return ChatResponseDTO(
            message_id=saved_message.id,
            query=dto.query,
            response=response,
            sources=sources,
            created_at=saved_message.created_at
        )