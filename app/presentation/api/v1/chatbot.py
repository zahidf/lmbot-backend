from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..schemas.chat_schemas import (
    ChatQueryRequest,
    ChatResponse,
    ChatSourceResponse,
    ChatHistoryResponse
)
from ..dependencies import (
    get_current_user,
    get_process_chat_query_use_case,
    get_chat_repository
)
from ....application.use_cases.chatbot.process_chat_query import ProcessChatQuery
from ....application.dtos.chat_dtos import ChatQueryDTO
from ....application.interfaces.repositories.chat_repository import ChatRepository

router = APIRouter(prefix="/chat", tags=["chatbot"])


@router.post("/query", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat_query(
    request: ChatQueryRequest,
    current_user = Depends(get_current_user),
    use_case: ProcessChatQuery = Depends(get_process_chat_query_use_case)
):
    """
    Process a chat query using RAG
    
    - **query**: User's question (1-2000 characters)
    
    Returns:
    - Generated response with source citations
    """
    try:
        # Create DTO
        dto = ChatQueryDTO(
            user_id=current_user["id"],
            query=request.query
        )
        
        # Execute and format response
        result = await use_case.execute(dto)
        return ChatResponse(
            message_id=result.message_id,
            query=result.query,
            response=result.response,
            sources=[
                ChatSourceResponse(**source)
                for source in result.sources
            ],
            created_at=result.created_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your query: {str(e)}"
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = 10,
    current_user = Depends(get_current_user),
    chat_repository: ChatRepository = Depends(get_chat_repository)
):
    """
    Get chat history for current user
    
    - **limit**: Number of messages to retrieve (default: 10, max: 50)
    """
    try:
        # Validate limit
        if limit > 50:
            limit = 50
        
        # Get history
        messages = await chat_repository.find_by_user_id(
            user_id=current_user["id"],
            limit=limit
        )
        
        # Format response
        return ChatHistoryResponse(
            messages=[
                ChatResponse(
                    message_id=msg.id,
                    query=msg.query,
                    response=msg.response,
                    sources=[], 
                    created_at=msg.created_at
                )
                for msg in messages
            ],
            total=len(messages)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )