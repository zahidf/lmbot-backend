import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from app.application.use_cases.documents.upload_document import UploadDocument
from app.application.dtos.document_dtos import (
    DocumentUploadDTO,
    DocumentUploadResponseDTO,
)
from app.domain.entities.document_upload import DocumentUpload


class TestUploadDocument:
    """Test UploadDocument use case"""

    @pytest.fixture
    def mock_document_repository(self):
        """Mock document repository"""
        repo = AsyncMock()

        async def save_mock(document):
            # Return the same document with an ID
            document.id = "doc-123"
            return document

        repo.save.side_effect = save_mock
        return repo

    @pytest.fixture
    def mock_file_storage_service(self):
        """Mock file storage service"""
        service = AsyncMock()
        service.save_file.return_value = "/uploads/tx_manual.pdf"
        return service

    @pytest.fixture
    def use_case(self, mock_document_repository, mock_file_storage_service):
        """Create use case with mocked dependencies"""
        return UploadDocument(
            document_repository=mock_document_repository,
            file_storage_service=mock_file_storage_service,
        )

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self, use_case, mock_file_storage_service, mock_document_repository
    ):
        """Test successful document upload"""
        # Arrange
        mock_file = Mock()
        mock_file.seek = AsyncMock()
        mock_file.filename = "tx_manual.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024000
        mock_file.read = AsyncMock(return_value=b"PDF content")

        dto = DocumentUploadDTO(
            file=mock_file,
            title="TX Series Manual",
            product_series="TX",
            category="Manual",
            uploaded_by="user-123",
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        assert isinstance(result, DocumentUploadResponseDTO)
        assert result.id == "doc-123"
        assert result.title == "TX Series Manual"
        assert result.file_name == "tx_manual.pdf"
        assert result.file_type == "pdf"
        assert result.is_processed is False

        # Verify service calls
        mock_file_storage_service.save_file.assert_called_once()
        mock_document_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_invalid_file_type(self, use_case):
        """Test upload with invalid file type"""
        # Arrange
        mock_file = Mock()
        mock_file.seek = AsyncMock()
        mock_file.filename = "malware.exe"
        mock_file.content_type = "application/x-executable"
        mock_file.size = 1000

        dto = DocumentUploadDTO(
            file=mock_file,
            title="Malware",
            product_series=None,
            category=None,
            uploaded_by="user-123",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid file type"):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_upload_document_file_too_large(self, use_case):
        """Test upload with file too large"""
        # Arrange
        mock_file = Mock()
        mock_file.seek = AsyncMock()
        mock_file.filename = "large.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 60 * 1024 * 1024  # 60 MB

        dto = DocumentUploadDTO(
            file=mock_file,
            title="Large Document",
            product_series=None,
            category=None,
            uploaded_by="user-123",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="File size exceeds maximum"):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_upload_document_with_optional_metadata(
        self, use_case, mock_document_repository
    ):
        """Test upload with optional metadata"""
        # Arrange
        mock_file = Mock()
        mock_file.seek = AsyncMock()
        mock_file.filename = "guide.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 500000
        mock_file.read = AsyncMock(return_value=b"PDF content")

        dto = DocumentUploadDTO(
            file=mock_file,
            title="Installation Guide",
            product_series="FD",
            category="Installation Guide",
            uploaded_by="admin-456",
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        saved_doc = mock_document_repository.save.call_args[0][0]
        assert saved_doc.product_series == "FD"
        assert saved_doc.category == "Installation Guide"

    @pytest.mark.asyncio
    async def test_upload_document_docx(self, use_case, mock_file_storage_service):
        """Test uploading DOCX file"""
        # Arrange
        mock_file = Mock()
        mock_file.seek = AsyncMock()
        mock_file.filename = "manual.docx"
        mock_file.content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        mock_file.size = 800000
        mock_file.read = AsyncMock(return_value=b"DOCX content")

        dto = DocumentUploadDTO(
            file=mock_file,
            title="Word Manual",
            product_series=None,
            category=None,
            uploaded_by="user-123",
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        assert result.file_type == "docx"
        mock_file_storage_service.save_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_txt(self, use_case):
        """Test uploading TXT file"""
        # Arrange
        mock_file = Mock()
        mock_file.seek = AsyncMock()
        mock_file.filename = "notes.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = 5000
        mock_file.read = AsyncMock(return_value=b"Text content")

        dto = DocumentUploadDTO(
            file=mock_file,
            title="Technical Notes",
            product_series=None,
            category=None,
            uploaded_by="user-123",
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        assert result.file_type == "txt"
