from datetime import datetime, timezone
from app.application.interfaces.repositories.document_repository import (
    DocumentRepository,
)
from app.application.interfaces.services.file_storage_service import FileStorageService
from app.application.dtos.document_dtos import (
    DocumentUploadDTO,
    DocumentUploadResponseDTO,
)
from app.domain.entities.document_upload import DocumentUpload


class UploadDocument:
    """
    Use Case: Upload document to knowledge base

    Flow:
    1. Validate file type and size
    2. Save file to storage
    3. Save document metadata to database
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        file_storage_service: FileStorageService,
    ):
        self.document_repository = document_repository
        self.file_storage_service = file_storage_service

    async def execute(self, dto: DocumentUploadDTO) -> DocumentUploadResponseDTO:
        """
        Upload document

        Args:
            dto: Document upload data

        Returns:
            DocumentUploadResponseDTO with saved document info

        Raises:
            ValueError: If file type or size is invalid
        """

        # Extract file info
        file_name = dto.file.filename
        file_type = self._extract_file_type(file_name)
        file_size = (
            dto.file.size if hasattr(dto.file, "size") else len(await dto.file.read())
        )

        # Reset file pointer if we read it for size
        if hasattr(dto.file, "seek") and file_size > 0:
            await dto.file.seek(0)

        document = DocumentUpload(
            id=None,
            title=dto.title,
            file_name=file_name,
            file_path="",  # Will be set after saving
            file_type=file_type,
            file_size=file_size,
            product_series=dto.product_series,
            category=dto.category,
            uploaded_by=dto.uploaded_by,
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(timezone.utc),
        )

        # Validate
        if not document.is_valid_file_type():
            raise ValueError(
                f"Invalid file type: {file_type}. "
                f"Allowed types: {', '.join(DocumentUpload.ALLOWED_FILE_TYPES)}"
            )

        if not document.is_valid_file_size():
            max_size_mb = DocumentUpload.MAX_FILE_SIZE / (1024 * 1024)
            raise ValueError(
                f"File size exceeds maximum allowed size of {max_size_mb}MB"
            )

        file_content = await dto.file.read()

        file_path = await self.file_storage_service.save_file(
            file_content=file_content,
            file_name=file_name,
            content_type=dto.file.content_type,
        )

        # Add file path
        document.file_path = file_path

        # Save metadata to database
        saved_document = await self.document_repository.save(document)

        # Return response
        return DocumentUploadResponseDTO(
            id=saved_document.id,
            title=saved_document.title,
            file_name=saved_document.file_name,
            file_path=saved_document.file_path,
            file_type=saved_document.file_type,
            file_size=saved_document.file_size,
            product_series=saved_document.product_series,
            category=saved_document.category,
            is_processed=saved_document.is_processed,
            chunk_count=saved_document.chunk_count,
            created_at=saved_document.created_at,
        )

    def _extract_file_type(self, file_name: str) -> str:
        """Extract file extension from filename"""
        return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
