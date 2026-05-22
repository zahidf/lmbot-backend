import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from app.application.use_cases.documents.process_document import ProcessDocument
from app.domain.entities.document_upload import DocumentUpload


class TestProcessDocument:
    """Test ProcessDocument use case"""

    @pytest.fixture
    def mock_document_repository(self):
        """Mock document repository"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_vector_store_repository(self):
        """Mock vector store repository"""
        return AsyncMock()

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service"""
        service = AsyncMock()
        service.generate_embedding.return_value = [0.1] * 1536  # OpenAI embedding size
        return service

    @pytest.fixture
    def mock_file_storage_service(self):
        """Mock file storage service"""
        service = AsyncMock()
        service.get_file.return_value = b"fake file bytes"
        return service

    @pytest.fixture
    def mock_document_processor(self):
        """Mock document processor service"""
        processor = AsyncMock()
        processor.extract_text.return_value = (
            "This is sample extracted text from the document. " * 50
        )
        return processor

    @pytest.fixture
    def mock_text_chunker(self):
        """Mock text chunker service"""
        chunker = Mock()
        chunker.chunk_text.return_value = [
            "This is chunk 1 with some content.",
            "This is chunk 2 with more content.",
            "This is chunk 3 with final content.",
        ]
        return chunker

    @pytest.fixture
    def sample_document(self):
        """Create sample document entity"""
        return DocumentUpload(
            id="doc-123",
            title="Test Manual",
            file_name="test_manual.pdf",
            file_path="/uploads/test_manual.pdf",
            file_type="pdf",
            file_size=1024000,
            product_series="TX",
            category="Manual",
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def use_case(
        self,
        mock_document_repository,
        mock_vector_store_repository,
        mock_llm_service,
        mock_file_storage_service,
        mock_document_processor,
        mock_text_chunker,
    ):
        """Create use case with mocked dependencies"""
        return ProcessDocument(
            document_repository=mock_document_repository,
            vector_store_repository=mock_vector_store_repository,
            llm_service=mock_llm_service,
            file_storage_service=mock_file_storage_service,
            document_processor=mock_document_processor,
            text_chunker=mock_text_chunker,
        )

    @pytest.mark.asyncio
    async def test_process_document_success(
        self,
        use_case,
        mock_document_repository,
        mock_document_processor,
        mock_text_chunker,
        mock_llm_service,
        sample_document,
    ):
        """Test successful document processing"""
        # Arrange
        mock_document_repository.find_by_id.return_value = sample_document

        with patch.object(
            use_case, "_store_chunk", new_callable=AsyncMock
        ) as mock_store:
            # Act
            result = await use_case.execute("doc-123")

        # Assert
        assert result["status"] == "processed"
        assert result["document_id"] == "doc-123"
        assert result["chunk_count"] == 3
        assert result["failed_chunks"] == 0
        assert "text_length" in result
        assert "processed_at" in result

        # Verify calls
        mock_document_repository.find_by_id.assert_called_once_with("doc-123")
        mock_document_processor.extract_text.assert_called_once_with(
            file_content=b"fake file bytes", file_type="pdf"
        )
        mock_text_chunker.chunk_text.assert_called_once()
        assert mock_llm_service.generate_embedding.call_count == 3
        mock_document_repository.save.assert_called_once()

        # Verify document marked as processed
        saved_doc = mock_document_repository.save.call_args[0][0]
        assert saved_doc.is_processed is True
        assert saved_doc.chunk_count == 3

    @pytest.mark.asyncio
    async def test_process_document_not_found(self, use_case, mock_document_repository):
        """Test processing non-existent document"""
        # Arrange
        mock_document_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Document doc-999 not found"):
            await use_case.execute("doc-999")

    @pytest.mark.asyncio
    async def test_process_document_already_processed(
        self, use_case, mock_document_repository, sample_document
    ):
        """Test processing already processed document"""
        # Arrange
        sample_document.is_processed = True
        sample_document.chunk_count = 5
        mock_document_repository.find_by_id.return_value = sample_document

        # Act
        result = await use_case.execute("doc-123")

        # Assert
        assert result["status"] == "already_processed"
        assert result["document_id"] == "doc-123"
        assert result["chunk_count"] == 5

    @pytest.mark.asyncio
    async def test_process_document_empty_text(
        self,
        use_case,
        mock_document_repository,
        mock_document_processor,
        sample_document,
    ):
        """Test processing document with empty/short text"""
        # Arrange
        mock_document_repository.find_by_id.return_value = sample_document
        mock_document_processor.extract_text.return_value = (
            "Short"  # Less than 50 chars
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Extracted text is too short or empty"):
            await use_case.execute("doc-123")

    @pytest.mark.asyncio
    async def test_process_document_no_chunks(
        self,
        use_case,
        mock_document_repository,
        mock_document_processor,
        mock_text_chunker,
        sample_document,
    ):
        """Test processing when chunker returns empty list"""
        # Arrange
        mock_document_repository.find_by_id.return_value = sample_document
        mock_text_chunker.chunk_text.return_value = []

        # Act & Assert
        with pytest.raises(ValueError, match="No chunks created from text"):
            await use_case.execute("doc-123")

    @pytest.mark.asyncio
    async def test_process_document_partial_chunk_failure(
        self, use_case, mock_document_repository, mock_llm_service, sample_document
    ):
        """Test processing with some chunks failing"""
        # Arrange
        mock_document_repository.find_by_id.return_value = sample_document

        # First chunk succeeds, second fails, third succeeds
        mock_llm_service.generate_embedding.side_effect = [
            [0.1] * 1536,
            Exception("Embedding failed"),
            [0.2] * 1536,
        ]

        with patch.object(
            use_case, "_store_chunk", new_callable=AsyncMock
        ) as mock_store:
            # Act
            result = await use_case.execute("doc-123")

        # Assert
        assert result["status"] == "processed"
        assert result["chunk_count"] == 2  # Only 2 succeeded
        assert result["failed_chunks"] == 1

    @pytest.mark.asyncio
    async def test_process_document_all_chunks_fail(
        self, use_case, mock_document_repository, mock_llm_service, sample_document
    ):
        """Test processing when all chunks fail"""
        # Arrange
        mock_document_repository.find_by_id.return_value = sample_document
        mock_llm_service.generate_embedding.side_effect = Exception(
            "Embedding service down"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="All chunks failed to process"):
            await use_case.execute("doc-123")

    @pytest.mark.asyncio
    async def test_process_document_chunk_metadata(
        self, use_case, mock_document_repository, mock_text_chunker, sample_document
    ):
        """Test that chunk metadata is correctly populated"""
        # Arrange
        mock_document_repository.find_by_id.return_value = sample_document
        mock_text_chunker.chunk_text.return_value = ["Single chunk content"]

        stored_metadata = None

        async def capture_store(document_id, chunk_index, content, embedding, metadata):
            nonlocal stored_metadata
            stored_metadata = metadata

        with patch.object(use_case, "_store_chunk", side_effect=capture_store):
            # Act
            await use_case.execute("doc-123")

        # Assert metadata structure
        assert stored_metadata is not None
        assert stored_metadata["document_id"] == "doc-123"
        assert stored_metadata["document_title"] == "Test Manual"
        assert stored_metadata["product_series"] == "TX"
        assert stored_metadata["category"] == "Manual"
        assert stored_metadata["file_name"] == "test_manual.pdf"
        assert stored_metadata["file_type"] == "pdf"
        assert stored_metadata["chunk_index"] == 0
        assert stored_metadata["total_chunks"] == 1
        assert "created_at" in stored_metadata

    @pytest.mark.asyncio
    async def test_process_document_docx_file(
        self,
        use_case,
        mock_document_repository,
        mock_document_processor,
        sample_document,
    ):
        """Test processing DOCX file"""
        # Arrange
        sample_document.file_type = "docx"
        sample_document.file_name = "manual.docx"
        sample_document.file_path = "/uploads/manual.docx"
        mock_document_repository.find_by_id.return_value = sample_document

        with patch.object(use_case, "_store_chunk", new_callable=AsyncMock):
            # Act
            result = await use_case.execute("doc-123")

        # Assert
        mock_document_processor.extract_text.assert_called_once_with(
            file_content=b"fake file bytes", file_type="docx"
        )
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_process_document_txt_file(
        self,
        use_case,
        mock_document_repository,
        mock_document_processor,
        sample_document,
    ):
        """Test processing TXT file"""
        # Arrange
        sample_document.file_type = "txt"
        sample_document.file_name = "notes.txt"
        sample_document.file_path = "/uploads/notes.txt"
        mock_document_repository.find_by_id.return_value = sample_document

        with patch.object(use_case, "_store_chunk", new_callable=AsyncMock):
            # Act
            result = await use_case.execute("doc-123")

        # Assert
        mock_document_processor.extract_text.assert_called_once_with(
            file_content=b"fake file bytes", file_type="txt"
        )
        assert result["status"] == "processed"
