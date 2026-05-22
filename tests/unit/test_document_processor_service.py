import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from app.infrastructure.external_services.document_processor_service import (
    DocumentProcessorService,
)


class TestDocumentProcessorService:
    """Test DocumentProcessorService"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return DocumentProcessorService()

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf(self, service):
        """Test extracting text from PDF file"""
        # Arrange
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch(
            "app.infrastructure.external_services.document_processor_service.pdfplumber.open",
            return_value=mock_pdf,
        ):
            # Act
            result = await service.extract_text("/path/to/doc.pdf", "pdf")

        # Assert
        assert "Page 1 content" in result
        assert "Page 2 content" in result
        assert "\n\n" in result  # Pages joined with double newline

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_with_empty_pages(self, service):
        """Test PDF extraction handles empty pages"""
        # Arrange
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Content page"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = None  # Empty page
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = ""  # Blank page

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch(
            "app.infrastructure.external_services.document_processor_service.pdfplumber.open",
            return_value=mock_pdf,
        ):
            # Act
            result = await service.extract_text("/path/to/doc.pdf", "pdf")

        # Assert
        assert result == "Content page"  # Only non-empty page included

    @pytest.mark.asyncio
    async def test_extract_text_from_docx(self, service):
        """Test extracting text from DOCX file"""
        # Arrange
        mock_para1 = Mock()
        mock_para1.text = "Paragraph 1"
        mock_para2 = Mock()
        mock_para2.text = "Paragraph 2"
        mock_para3 = Mock()
        mock_para3.text = "  "  # Whitespace only

        mock_doc = Mock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]

        with patch(
            "app.infrastructure.external_services.document_processor_service.DocxDocument",
            return_value=mock_doc,
        ):
            # Act
            result = await service.extract_text("/path/to/doc.docx", "docx")

        # Assert
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result
        assert "\n\n" in result

    @pytest.mark.asyncio
    async def test_extract_text_from_docx_with_doc_extension(self, service):
        """Test extracting text from .doc file"""
        # Arrange
        mock_para = Mock()
        mock_para.text = "Document content"

        mock_doc = Mock()
        mock_doc.paragraphs = [mock_para]

        with patch(
            "app.infrastructure.external_services.document_processor_service.DocxDocument",
            return_value=mock_doc,
        ):
            # Act
            result = await service.extract_text("/path/to/doc.doc", "doc")

        # Assert
        assert result == "Document content"

    @pytest.mark.asyncio
    async def test_extract_text_from_txt(self, service):
        """Test extracting text from TXT file"""
        # Arrange
        file_content = "This is plain text content.\nWith multiple lines."

        with patch("builtins.open", mock_open(read_data=file_content)):
            # Act
            result = await service.extract_text("/path/to/doc.txt", "txt")

        # Assert
        assert result == file_content

    @pytest.mark.asyncio
    async def test_extract_text_from_txt_with_unicode(self, service):
        """Test extracting text from TXT with unicode characters"""
        # Arrange
        file_content = "Unicode content: café, naïve, 日本語"

        with patch("builtins.open", mock_open(read_data=file_content)):
            # Act
            result = await service.extract_text("/path/to/unicode.txt", "txt")

        # Assert
        assert result == file_content

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_file_type(self, service):
        """Test extraction with unsupported file type"""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported file type: xlsx"):
            await service.extract_text("/path/to/doc.xlsx", "xlsx")

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_file_type_exe(self, service):
        """Test extraction with executable file type"""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported file type: exe"):
            await service.extract_text("/path/to/file.exe", "exe")

    @pytest.mark.asyncio
    async def test_extract_text_pdf_file_not_found(self, service):
        """Test PDF extraction when file doesn't exist"""
        # Arrange
        with patch(
            "app.infrastructure.external_services.document_processor_service.pdfplumber.open",
            side_effect=FileNotFoundError("File not found"),
        ):
            # Act & Assert
            with pytest.raises(FileNotFoundError):
                await service.extract_text("/nonexistent/path.pdf", "pdf")

    @pytest.mark.asyncio
    async def test_extract_text_docx_file_not_found(self, service):
        """Test DOCX extraction when file doesn't exist"""
        # Arrange
        with patch(
            "app.infrastructure.external_services.document_processor_service.DocxDocument",
            side_effect=FileNotFoundError("File not found"),
        ):
            # Act & Assert
            with pytest.raises(FileNotFoundError):
                await service.extract_text("/nonexistent/path.docx", "docx")

    @pytest.mark.asyncio
    async def test_extract_text_txt_file_not_found(self, service):
        """Test TXT extraction when file doesn't exist"""
        # Arrange
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            # Act & Assert
            with pytest.raises(FileNotFoundError):
                await service.extract_text("/nonexistent/path.txt", "txt")

    @pytest.mark.asyncio
    async def test_extract_text_pdf_multipage(self, service):
        """Test extracting text from multi-page PDF"""
        # Arrange
        pages = []
        for i in range(5):
            mock_page = Mock()
            mock_page.extract_text.return_value = f"Page {i + 1} content"
            pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = pages
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch(
            "app.infrastructure.external_services.document_processor_service.pdfplumber.open",
            return_value=mock_pdf,
        ):
            # Act
            result = await service.extract_text("/path/to/multipage.pdf", "pdf")

        # Assert
        for i in range(5):
            assert f"Page {i + 1} content" in result

    @pytest.mark.asyncio
    async def test_extract_text_docx_empty_paragraphs_filtered(self, service):
        """Test that empty paragraphs are filtered from DOCX"""
        # Arrange
        mock_paras = [
            Mock(text="Content 1"),
            Mock(text=""),
            Mock(text="   "),
            Mock(text="\n\t"),
            Mock(text="Content 2"),
        ]

        mock_doc = Mock()
        mock_doc.paragraphs = mock_paras

        with patch(
            "app.infrastructure.external_services.document_processor_service.DocxDocument",
            return_value=mock_doc,
        ):
            # Act
            result = await service.extract_text("/path/to/doc.docx", "docx")

        # Assert
        assert result == "Content 1\n\nContent 2"
