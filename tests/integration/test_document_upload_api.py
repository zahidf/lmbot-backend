import pytest
import io
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestDocumentUploadAPI:
    """Integration tests for document upload API"""

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"Authorization": "Bearer test-token"}

    def test_upload_document_pdf_success(self, auth_headers):
        """Test successful PDF upload"""
        # Arrange
        file_content = b"PDF file content"
        files = {
            "file": ("test_manual.pdf", io.BytesIO(file_content), "application/pdf")
        }
        data = {"title": "Test Manual", "product_series": "TX", "category": "Manual"}

        # Act
        response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["title"] == "Test Manual"
        assert result["file_name"] == "test_manual.pdf"
        assert result["file_type"] == "pdf"
        assert result["product_series"] == "TX"
        assert result["category"] == "Manual"
        assert result["is_processed"] is False

    def test_upload_document_docx_success(self, auth_headers):
        """Test successful DOCX upload"""
        # Arrange
        file_content = b"DOCX file content"
        files = {
            "file": (
                "guide.docx",
                io.BytesIO(file_content),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        data = {"title": "Installation Guide"}

        # Act
        response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        result = response.json()
        assert result["file_type"] == "docx"

    def test_upload_document_txt_success(self, auth_headers):
        """Test successful TXT upload"""
        # Arrange
        file_content = b"Text file content"
        files = {"file": ("notes.txt", io.BytesIO(file_content), "text/plain")}
        data = {"title": "Technical Notes"}

        # Act
        response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        result = response.json()
        assert result["file_type"] == "txt"

    def test_upload_document_invalid_file_type(self, auth_headers):
        """Test upload with invalid file type"""
        # Arrange
        file_content = b"Executable content"
        files = {
            "file": (
                "malware.exe",
                io.BytesIO(file_content),
                "application/x-executable",
            )
        }
        data = {"title": "Malware"}

        # Act
        response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_document_missing_title(self, auth_headers):
        """Test upload without title"""
        # Arrange
        file_content = b"PDF content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

        # Act
        response = client.post(
            "/api/v1/documents/upload", files=files, headers=auth_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error

    def test_upload_document_unauthenticated(self):
        """Test upload without authentication"""
        # Arrange
        file_content = b"PDF content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        data = {"title": "Test"}

        # Act
        response = client.post("/api/v1/documents/upload", files=files, data=data)

        # Assert
        assert response.status_code == 401

    def test_upload_document_with_optional_metadata(self, auth_headers):
        """Test upload with all optional metadata"""
        # Arrange
        file_content = b"PDF content"
        files = {"file": ("manual.pdf", io.BytesIO(file_content), "application/pdf")}
        data = {
            "title": "Complete Manual",
            "product_series": "HC",
            "category": "Installation Guide",
        }

        # Act
        response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        result = response.json()
        assert result["product_series"] == "HC"
        assert result["category"] == "Installation Guide"

    def test_list_documents(self, auth_headers):
        """Test listing uploaded documents"""
        # Act
        response = client.get("/api/v1/documents", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "documents" in result
        assert isinstance(result["documents"], list)

    def test_get_document_by_id(self, auth_headers):
        """Test getting document by ID"""
        # Upload document
        file_content = b"PDF content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        data = {"title": "Test Document"}

        upload_response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        doc_id = upload_response.json()["id"]

        # Act
        response = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == doc_id
        assert result["title"] == "Test Document"

    def test_delete_document(self, auth_headers):
        """Test deleting a document"""
        # Upload document
        file_content = b"PDF content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        data = {"title": "Test Document"}

        upload_response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        doc_id = upload_response.json()["id"]

        # Act
        response = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Document deleted successfully"

    def test_get_document_status_pending(self, auth_headers):
        """Test getting status of unprocessed document"""
        # Upload document first
        file_content = b"PDF content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        data = {"title": "Status Test Document"}

        upload_response = client.post(
            "/api/v1/documents/upload", files=files, data=data, headers=auth_headers
        )

        doc_id = upload_response.json()["id"]

        # Act
        response = client.get(
            f"/api/v1/documents/{doc_id}/status", headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["document_id"] == doc_id
        assert result["is_processed"] is False
        assert result["status"] == "pending"
        assert result["chunk_count"] == 0

    def test_get_document_status_not_found(self, auth_headers):
        """Test getting status of non-existent document"""
        # Act
        response = client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/status",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_document_status_unauthenticated(self):
        """Test getting status without authentication"""
        # Act
        response = client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/status"
        )

        # Assert
        assert response.status_code == 401

    def test_process_document_not_found(self, auth_headers):
        """Test processing non-existent document"""
        # Act
        response = client.post(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/process",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_process_document_unauthenticated(self):
        """Test processing document without authentication"""
        # Act
        response = client.post(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/process"
        )

        # Assert
        assert response.status_code == 401
