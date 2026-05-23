from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from app.application.dtos.library_dtos import (
    LibraryBrowseDTO,
    LibraryCreateFolderDTO,
    LibraryUploadFileDTO,
)
from app.application.use_cases.library.browse_library_items import BrowseLibraryItems
from app.application.use_cases.library.create_library_folder import CreateLibraryFolder
from app.application.use_cases.library.delete_library_file import DeleteLibraryFile
from app.application.use_cases.library.delete_library_folder import DeleteLibraryFolder
from app.application.use_cases.library.upload_library_file import UploadLibraryFile
from app.domain.entities.library_file import LibraryFile
from app.domain.entities.library_folder import LibraryFolder

USER_ID = "4ecd20df-5594-4861-b40f-58fdda198b18"


def _folder(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid.uuid4()),
        "name": "TX",
        "parent_id": None,
        "type": "Manual",
        "description": None,
        "created_by": USER_ID,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return LibraryFolder(**data)


def _file(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid.uuid4()),
        "folder_id": str(uuid.uuid4()),
        "display_name": "TX Manual",
        "original_file_name": "tx.pdf",
        "storage_path": "stored.pdf",
        "content_type": "application/pdf",
        "file_extension": "pdf",
        "size_bytes": 100,
        "type": "Manual",
        "description": None,
        "uploaded_by": USER_ID,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return LibraryFile(**data)


@pytest.mark.asyncio
async def test_create_folder_rejects_duplicate_sibling_name():
    repo = SimpleNamespace()
    repo.get_folder = AsyncMock()
    repo.folder_name_exists = AsyncMock(return_value=True)
    repo.save_folder = AsyncMock()
    use_case = CreateLibraryFolder(repo)

    with pytest.raises(ValueError, match="already exists"):
        await use_case.execute(
            LibraryCreateFolderDTO(
                name="TX",
                parent_id=None,
                type="Manual",
                description=None,
                created_by=USER_ID,
            )
        )

    repo.save_folder.assert_not_called()


@pytest.mark.asyncio
async def test_delete_folder_rejects_non_empty_folder():
    folder = _folder()
    repo = SimpleNamespace()
    repo.get_folder = AsyncMock(return_value=folder)
    repo.folder_has_children = AsyncMock(return_value=True)
    repo.delete_folder = AsyncMock()
    use_case = DeleteLibraryFolder(repo)

    with pytest.raises(ValueError, match="empty"):
        await use_case.execute(folder.id)

    repo.delete_folder.assert_not_called()


@pytest.mark.asyncio
async def test_upload_file_saves_storage_and_metadata():
    folder = _folder()
    repo = SimpleNamespace()
    repo.get_folder = AsyncMock(return_value=folder)
    repo.file_name_exists = AsyncMock(return_value=False)

    async def save_file(file):
        data = file.__dict__.copy()
        data["id"] = str(uuid.uuid4())
        return _file(**data)

    repo.save_file = AsyncMock(side_effect=save_file)
    storage = SimpleNamespace()
    storage.save_file = AsyncMock(return_value="library/tx.pdf")

    upload = SimpleNamespace(
        filename="tx.pdf",
        content_type="application/pdf",
        size=12,
        read=AsyncMock(return_value=b"manual bytes"),
    )
    use_case = UploadLibraryFile(repo, storage)

    result = await use_case.execute(
        LibraryUploadFileDTO(
            file=upload,
            folder_id=folder.id,
            type="Manual",
            display_name="TX Manual",
            description="Install guide",
            uploaded_by=USER_ID,
        )
    )

    assert result.storage_path == "library/tx.pdf"
    storage.save_file.assert_called_once_with(
        file_content=b"manual bytes",
        file_name="tx.pdf",
        content_type="application/pdf",
    )
    repo.save_file.assert_called_once()


@pytest.mark.asyncio
async def test_delete_file_deletes_blob_and_metadata():
    file = _file()
    repo = SimpleNamespace()
    repo.get_file = AsyncMock(return_value=file)
    repo.delete_file = AsyncMock(return_value=True)
    storage = SimpleNamespace()
    storage.delete_file = AsyncMock(return_value=True)
    use_case = DeleteLibraryFile(repo, storage)

    result = await use_case.execute(file.id)

    assert result == file.id
    storage.delete_file.assert_called_once_with(file.storage_path)
    repo.delete_file.assert_called_once_with(file.id)


@pytest.mark.asyncio
async def test_browse_library_filters_and_sorts_items():
    now = datetime.now(timezone.utc)
    folder = _folder(id="00000000-0000-0000-0000-000000000001", created_at=now)
    older_file = _file(
        folder_id=folder.id,
        display_name="Old Manual",
        type="Manual",
        size_bytes=50,
        created_at=now - timedelta(days=1),
    )
    newer_file = _file(
        folder_id=folder.id,
        display_name="New Manual",
        type="Manual",
        size_bytes=500,
        created_at=now,
    )

    repo = SimpleNamespace()
    repo.get_folder = AsyncMock(return_value=folder)
    repo.get_breadcrumbs = AsyncMock(return_value=[folder])
    repo.list_folders = AsyncMock(return_value=[])
    repo.list_files = AsyncMock(return_value=[older_file, newer_file])
    repo.list_folders_recursive = AsyncMock(return_value=[])
    repo.list_files_recursive = AsyncMock(return_value=[older_file, newer_file])
    repo.get_folder_child_counts = AsyncMock(return_value={})
    repo.get_folder_child_file_sizes = AsyncMock(return_value={})
    use_case = BrowseLibraryItems(repo)

    result = await use_case.execute(
        LibraryBrowseDTO(
            folder_id=folder.id,
            search="manual",
            type="manuals",
            date=None,
            size="largest",
            limit=10,
            offset=0,
        )
    )

    assert [item.name for item in result.items] == ["New Manual", "Old Manual"]
    assert result.total == 2
