import pytest
from datetime import datetime, UTC
from app.domain.entities.document_upload import DocumentUpload


class TestDocumentUpload:
    """Test DocumentUpload entity"""

    def test_create_document_upload(self):
        """Test creating a document upload entity"""
        doc = DocumentUpload(
            id=None,
            title="TX Series Manual",
            file_name="tx_manual.pdf",
            file_path="/uploads/tx_manual.pdf",
            file_type="pdf",
            file_size=1024000,
            product_series="TX",
            category="Manual",
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        assert doc.title == "TX Series Manual"
        assert doc.file_name == "tx_manual.pdf"
        assert doc.file_type == "pdf"
        assert doc.file_size == 1024000
        assert doc.product_series == "TX"
        assert doc.is_processed is False

    def test_validate_file_type_pdf(self):
        """Test PDF file type validation"""
        doc = DocumentUpload(
            id=None,
            title="Test",
            file_name="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="pdf",
            file_size=1000,
            product_series=None,
            category=None,
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        assert doc.is_valid_file_type() is True

    def test_validate_file_type_docx(self):
        """Test DOCX file type validation"""
        doc = DocumentUpload(
            id=None,
            title="Test",
            file_name="test.docx",
            file_path="/uploads/test.docx",
            file_type="docx",
            file_size=1000,
            product_series=None,
            category=None,
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        assert doc.is_valid_file_type() is True

    def test_validate_file_type_txt(self):
        """Test TXT file type validation"""
        doc = DocumentUpload(
            id=None,
            title="Test",
            file_name="test.txt",
            file_path="/uploads/test.txt",
            file_type="txt",
            file_size=1000,
            product_series=None,
            category=None,
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        assert doc.is_valid_file_type() is True

    def test_validate_file_type_invalid(self):
        """Test invalid file type"""
        doc = DocumentUpload(
            id=None,
            title="Test",
            file_name="test.exe",
            file_path="/uploads/test.exe",
            file_type="exe",
            file_size=1000,
            product_series=None,
            category=None,
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        assert doc.is_valid_file_type() is False

    def test_validate_file_size_valid(self):
        """Test valid file size (under 50MB)"""
        doc = DocumentUpload(
            id=None,
            title="Test",
            file_name="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="pdf",
            file_size=10 * 1024 * 1024,  # 10 MB
            product_series=None,
            category=None,
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        assert doc.is_valid_file_size() is True

    def test_validate_file_size_too_large(self):
        """Test file size too large (over 50MB)"""
        doc = DocumentUpload(
            id=None,
            title="Test",
            file_name="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="pdf",
            file_size=60 * 1024 * 1024,  # 60 MB
            product_series=None,
            category=None,
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        assert doc.is_valid_file_size() is False

    def test_mark_as_processed(self):
        """Test marking document as processed"""
        doc = DocumentUpload(
            id="doc-123",
            title="Test",
            file_name="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="pdf",
            file_size=1000,
            product_series=None,
            category=None,
            uploaded_by="user-123",
            is_processed=False,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )

        doc.mark_as_processed(chunk_count=10)

        assert doc.is_processed is True
        assert doc.chunk_count == 10
