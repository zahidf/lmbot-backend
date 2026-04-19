import os
import pytest
from pathlib import Path
from unittest.mock import patch
from app.infrastructure.external_services.local_file_storage_service import LocalFileStorageService


class TestLocalFileStorageService:
    """Unit tests for LocalFileStorageService using a temporary directory"""

    @pytest.fixture
    def service(self, tmp_path):
        """Storage service backed by a pytest-managed temp directory"""
        return LocalFileStorageService(upload_dir=str(tmp_path))

    # ── save_file ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_save_file_creates_file(self, service, tmp_path):
        """Saved file exists on disk and has the correct extension"""
        content = b"Hello, this is test file content for a PDF document."
        path = await service.save_file(content, "test_manual.pdf", "application/pdf")

        assert os.path.exists(path)
        assert path.endswith(".pdf")

    @pytest.mark.asyncio
    async def test_save_file_content_is_correct(self, service):
        """The bytes written match the bytes passed to save_file"""
        content = b"Exact content check"
        path = await service.save_file(content, "check.txt", "text/plain")

        with open(path, "rb") as f:
            assert f.read() == content

    @pytest.mark.asyncio
    async def test_save_file_generates_unique_names(self, service):
        """Saving the same filename twice produces two different file paths"""
        content = b"duplicate name test"
        path1 = await service.save_file(content, "doc.pdf", "application/pdf")
        path2 = await service.save_file(content, "doc.pdf", "application/pdf")

        assert path1 != path2
        assert os.path.exists(path1)
        assert os.path.exists(path2)

    @pytest.mark.asyncio
    async def test_save_file_no_extension(self, service):
        """Files with no extension are saved without a trailing dot"""
        content = b"no extension content"
        path = await service.save_file(content, "noext", "application/octet-stream")

        assert os.path.exists(path)
        assert not path.endswith(".")

    # ── delete_file ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_file_existing_file(self, service):
        """Deleting an existing file returns True and removes it from disk"""
        content = b"deletable content"
        path = await service.save_file(content, "todelete.pdf", "application/pdf")
        assert os.path.exists(path)

        result = await service.delete_file(path)

        assert result is True
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_delete_file_nonexistent_file(self, service):
        """Deleting a path that does not exist returns False"""
        result = await service.delete_file("/nonexistent/path/to/file.pdf")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_exception_returns_false(self, service):
        """If unlink raises an exception, delete_file returns False gracefully"""
        content = b"content for unlink patch test"
        path = await service.save_file(content, "patch_test.pdf", "application/pdf")

        with patch("pathlib.Path.unlink", side_effect=PermissionError("Access denied")):
            result = await service.delete_file(path)

        assert result is False

    # ── get_file ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_file_reads_content(self, service):
        """get_file returns the same bytes that were written by save_file"""
        content = b"Read back this exact content"
        path = await service.save_file(content, "readable.txt", "text/plain")

        result = await service.get_file(path)

        assert result == content

    @pytest.mark.asyncio
    async def test_get_file_nonexistent_raises(self, service):
        """get_file raises FileNotFoundError for a path that does not exist"""
        with pytest.raises(FileNotFoundError):
            await service.get_file("/nonexistent/path/missing.txt")
