from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from ...infrastructure.persistence.database import get_db
from ...infrastructure.external_services.langchain_llm_service import LangChainLLMService
from ...infrastructure.persistence.repositories.langchain_vector_store_repository import (
    LangChainVectorStoreRepository
)
from ...infrastructure.persistence.repositories.chat_repository_impl import ChatRepositoryImpl
from ...infrastructure.persistence.repositories.chat_session_repository_impl import ChatSessionRepositoryImpl
from ...infrastructure.persistence.repositories.chat_triage_repository_impl import ChatTriageRepositoryImpl
from app.infrastructure.persistence.repositories.document_repository_impl import DocumentRepositoryImpl
from app.infrastructure.persistence.repositories.ticket_repository_impl import TicketRepositoryImpl
from app.infrastructure.persistence.repositories.ticket_activity_repository_impl import TicketActivityRepositoryImpl
from ...application.use_cases.chatbot.process_chat_query import ProcessChatQuery
from ...application.use_cases.chatbot.submit_triage import SubmitTriage
from app.application.use_cases.documents.upload_document import UploadDocument
from app.application.use_cases.documents.process_document import ProcessDocument
from app.application.use_cases.tickets.escalate_ticket import EscalateTicket
from app.infrastructure.external_services.local_file_storage_service import LocalFileStorageService
from app.infrastructure.external_services.document_processor_service import DocumentProcessorService
from app.infrastructure.external_services.semantic_text_chunking_service import SemanticTextChunkerService
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
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    # Mock user for testing
    return {
        "id": "4ecd20df-5594-4861-b40f-58fdda198b18",
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

def get_file_storage_service() -> LocalFileStorageService:
    """Get file storage service singleton"""
    return LocalFileStorageService()

def get_document_processor_service() -> DocumentProcessorService:
    """Get document processor service singleton"""
    return DocumentProcessorService()


def get_text_chunker_service(
    llm_service: LangChainLLMService = Depends(get_llm_service),
) -> SemanticTextChunkerService:
    return SemanticTextChunkerService(
        embeddings=llm_service.embeddings,
        breakpoint_threshold_type=settings.SEMANTIC_CHUNKING_BREAKPOINT_THRESHOLD_TYPE,
        breakpoint_threshold_amount=settings.SEMANTIC_CHUNKING_BREAKPOINT_THRESHOLD,
        min_chunk_size=settings.SEMANTIC_CHUNKING_MIN_CHUNK_SIZE,
        max_chunk_size=settings.SEMANTIC_CHUNKING_MAX_CHUNK_SIZE,
        chunk_overlap=settings.SEMANTIC_CHUNKING_CHUNK_OVERLAP,
    )


# Repositories
async def get_vector_store_repository(
    session: AsyncSession = Depends(get_db)
) -> LangChainVectorStoreRepository:
    return LangChainVectorStoreRepository(session)


async def get_chat_repository(
    session: AsyncSession = Depends(get_db)
) -> ChatRepositoryImpl:
    return ChatRepositoryImpl(session)


async def get_chat_session_repository(
    session: AsyncSession = Depends(get_db)
) -> ChatSessionRepositoryImpl:
    return ChatSessionRepositoryImpl(session)


async def get_chat_triage_repository(
    session: AsyncSession = Depends(get_db)
) -> ChatTriageRepositoryImpl:
    return ChatTriageRepositoryImpl(session)


async def get_document_repository(
    session: AsyncSession = Depends(get_db)
) -> DocumentRepositoryImpl:
    return DocumentRepositoryImpl(session)


async def get_ticket_repository(
    session: AsyncSession = Depends(get_db)
) -> TicketRepositoryImpl:
    return TicketRepositoryImpl(session)


async def get_ticket_activity_repository(
    session: AsyncSession = Depends(get_db)
) -> TicketActivityRepositoryImpl:
    return TicketActivityRepositoryImpl(session)


# Use Cases
async def get_process_chat_query_use_case(
    session: AsyncSession = Depends(get_db),
    llm_service: LangChainLLMService = Depends(get_llm_service)
) -> ProcessChatQuery:
    """Get ProcessChatQuery use case — all repos share the same DB session"""
    return ProcessChatQuery(
        chat_repository=ChatRepositoryImpl(session),
        chat_session_repository=ChatSessionRepositoryImpl(session),
        triage_repository=ChatTriageRepositoryImpl(session),
        vector_store_repository=LangChainVectorStoreRepository(session),
        llm_service=llm_service,
        ticket_repository=TicketRepositoryImpl(session),
        ticket_activity_repository=TicketActivityRepositoryImpl(session),
    )


async def get_submit_triage_use_case(
    session: AsyncSession = Depends(get_db),
) -> SubmitTriage:
    return SubmitTriage(
        triage_repository=ChatTriageRepositoryImpl(session),
        session_repository=ChatSessionRepositoryImpl(session),
        ticket_repository=TicketRepositoryImpl(session),
        ticket_activity_repository=TicketActivityRepositoryImpl(session),
    )


async def get_escalate_ticket_use_case(
    session: AsyncSession = Depends(get_db),
    llm_service: LangChainLLMService = Depends(get_llm_service),
) -> EscalateTicket:
    return EscalateTicket(
        ticket_repository=TicketRepositoryImpl(session),
        ticket_activity_repository=TicketActivityRepositoryImpl(session),
        chat_repository=ChatRepositoryImpl(session),
        llm_service=llm_service,
    )


async def get_upload_document_use_case(
    document_repo: DocumentRepositoryImpl = Depends(get_document_repository),
    file_storage: LocalFileStorageService = Depends(get_file_storage_service)
) -> UploadDocument:
    return UploadDocument(
        document_repository=document_repo,
        file_storage_service=file_storage
    )

async def get_process_document_use_case(
    document_repo: DocumentRepositoryImpl = Depends(get_document_repository),
    vector_repo: LangChainVectorStoreRepository = Depends(get_vector_store_repository),
    llm_service: LangChainLLMService = Depends(get_llm_service),
    document_processor: DocumentProcessorService = Depends(get_document_processor_service),
    text_chunker: SemanticTextChunkerService = Depends(get_text_chunker_service)
) -> ProcessDocument:
    return ProcessDocument(
        document_repository=document_repo,
        vector_store_repository=vector_repo,
        llm_service=llm_service,
        document_processor=document_processor,
        text_chunker=text_chunker
    )
