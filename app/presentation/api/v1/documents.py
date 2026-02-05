from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, List
from app.presentation.api.schemas.document_schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentListItem,
    DocumentDeleteResponse
)
from app.presentation.api.dependencies import (
    get_current_user,
    get_upload_document_use_case,
    get_document_repository,
    get_process_document_use_case
)
from app.application.use_cases.documents.upload_document import UploadDocument
from app.application.use_cases.documents.process_document import ProcessDocument
from app.application.dtos.document_dtos import DocumentUploadDTO
from app.application.interfaces.repositories.document_repository import DocumentRepository
import logging
import traceback

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    product_series: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    use_case: UploadDocument = Depends(get_upload_document_use_case)
):
    """
    Upload a document to the knowledge base
    
    - **file**: Document file (PDF, DOCX, DOC, TXT) - max 50MB
    - **title**: Document title
    - **product_series**: Optional product series (TX, FD, HC, KS)
    - **category**: Optional document category
    
    Returns:
    - Document metadata with upload confirmation
    """
    try:
        # Create DTO
        dto = DocumentUploadDTO(
            file=file,
            title=title,
            product_series=product_series,
            category=category,
            uploaded_by=current_user["id"]
        )
        
        # Execute use case
        result = await use_case.execute(dto)
        
        # Return response
        return DocumentUploadResponse(
            id=result.id,
            title=result.title,
            file_name=result.file_name,
            file_path=result.file_path,
            file_type=result.file_type,
            file_size=result.file_size,
            product_series=result.product_series,
            category=result.category,
            is_processed=result.is_processed,
            chunk_count=result.chunk_count,
            created_at=result.created_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = 100,
    offset: int = 0,
    product_series: Optional[str] = None,
    category: Optional[str] = None,
    current_user = Depends(get_current_user),
    document_repository: DocumentRepository = Depends(get_document_repository)
):
    """
    List all uploaded documents
    
    - **limit**: Maximum number of documents to return (default: 100)
    - **offset**: Number of documents to skip (default: 0)
    - **product_series**: Filter by product series
    - **category**: Filter by category
    """
    try:
        documents = await document_repository.find_all(
            limit=limit,
            offset=offset,
            product_series=product_series,
            category=category
        )
        
        return DocumentListResponse(
            documents=[
                DocumentListItem(
                    id=doc.id,
                    title=doc.title,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    product_series=doc.product_series,
                    category=doc.category,
                    is_processed=doc.is_processed,
                    created_at=doc.created_at
                )
                for doc in documents
            ],
            total=len(documents)
        )
        
    except Exception as e:
        logger.error(f"List failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentUploadResponse)
async def get_document(
    document_id: str,
    current_user = Depends(get_current_user),
    document_repository: DocumentRepository = Depends(get_document_repository)
):
    """
    Get document by ID
    
    - **document_id**: Document UUID
    """
    try:
        document = await document_repository.find_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentUploadResponse(
            id=document.id,
            title=document.title,
            file_name=document.file_name,
            file_path=document.file_path,
            file_type=document.file_type,
            file_size=document.file_size,
            product_series=document.product_series,
            category=document.category,
            is_processed=document.is_processed,
            chunk_count=document.chunk_count,
            created_at=document.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(e)}"
        )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_user),
    document_repository: DocumentRepository = Depends(get_document_repository)
):
    """
    Delete document by ID
    
    - **document_id**: Document UUID
    """
    try:
        deleted = await document_repository.delete(document_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentDeleteResponse(
            message="Document deleted successfully",
            id=document_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def process_document(
    document_id: str,
    current_user = Depends(get_current_user),
    use_case: ProcessDocument = Depends(get_process_document_use_case)
):
    """
    Process document for RAG (Phase 2)
    
    This endpoint:
    1. Extracts text from the uploaded document
    2. Splits text into chunks (1000 chars with 200 overlap)
    3. Generates embeddings for each chunk
    4. Stores chunks in vector database
    5. Marks document as processed
    
    - **document_id**: UUID of the document to process
    
    Returns:
    - Processing status and statistics
    """
    try:
        logger.info(f"Processing document: {document_id}")
        result = await use_case.execute(document_id)
        
        return {
            "message": "Document processing completed",
            "status": result["status"],
            "document_id": document_id,
            "chunk_count": result.get("chunk_count", 0),
            "failed_chunks": result.get("failed_chunks", 0),
            "text_length": result.get("text_length", 0),
            "processed_at": result.get("processed_at")
        }
        
    except ValueError as e:
        logger.warning(f"Processing validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Processing failed for {document_id}: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    current_user = Depends(get_current_user),
    document_repository: DocumentRepository = Depends(get_document_repository)
):
    """
    Get document processing status
    
    - **document_id**: UUID of the document
    
    Returns:
    - Processing status (processed/not processed)
    - Chunk count if processed
    """
    try:
        document = await document_repository.find_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {
            "document_id": document_id,
            "title": document.title,
            "is_processed": document.is_processed,
            "chunk_count": document.chunk_count,
            "status": "ready" if document.is_processed else "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get status failed: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )