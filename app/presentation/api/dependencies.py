from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from ...infrastructure.persistence.database import get_db
from ...infrastructure.external_services.langchain_llm_service import LangChainLLMService
from ...infrastructure.persistence.repositories.langchain_vector_store_repository import (
    LangChainVectorStoreRepository
)
from ...infrastructure.persistence.repositories.chat_repository_impl import ChatRepositoryImpl
from ...application.use_cases.chatbot.process_chat_query import ProcessChatQuery
from ...infrastructure.config.settings import get_settings

security = HTTPBearer()
settings = get_settings()


# Authentication
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user
    TODO: Implement proper JWT validation
    """
    # Todo: make jwt validation
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    # Mock user for testing
    return {
        "id": "d5f5d537-cf95-47bc-85f1-007206a64477",
        "email": "user@example.com"
    }


# Services
def get_llm_service() -> LangChainLLMService:
    """Get LLM service singleton"""
    return LangChainLLMService(
        openai_api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        embedding_model=settings.OPENAI_EMBEDDING_MODEL,
        temperature=settings.OPENAI_TEMPERATURE
    )


# Repositories
async def get_vector_store_repository(
    session: AsyncSession = Depends(get_db)
) -> LangChainVectorStoreRepository:
    """Get vector store repository"""
    return LangChainVectorStoreRepository(session)


async def get_chat_repository(
    session: AsyncSession = Depends(get_db)
) -> ChatRepositoryImpl:
    """Get chat repository"""
    return ChatRepositoryImpl(session)


# Use Cases
async def get_process_chat_query_use_case(
    chat_repo: ChatRepositoryImpl = Depends(get_chat_repository),
    vector_repo: LangChainVectorStoreRepository = Depends(get_vector_store_repository),
    llm_service: LangChainLLMService = Depends(get_llm_service)
) -> ProcessChatQuery:
    """Get ProcessChatQuery use case"""
    return ProcessChatQuery(
        chat_repository=chat_repo,
        vector_store_repository=vector_repo,
        llm_service=llm_service
    )