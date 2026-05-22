from datetime import datetime, timezone
import uuid

import pytest

from app.domain.entities.library_file import LibraryFile
from app.domain.entities.library_folder import LibraryFolder
from app.presentation.api.dependencies import (
    get_file_storage_service,
    get_library_repository,
)

USER_ID = "4ecd20df-5594-4861-b40f-58fdda198b18"


class FakeLibraryRepository:
    def __init__(self):
        self.folders = {}
        self.files = {}

    async def save_folder(self, folder):
        folder.id = str(uuid.uuid4())
        self.folders[folder.id] = folder
        return folder

    async def get_folder(self, folder_id):
        return self.folders.get(folder_id)

    async def update_folder(self, folder):
        self.folders[folder.id] = folder
        return folder

    async def delete_folder(self, folder_id):
        return self.folders.pop(folder_id, None) is not None

    async def list_folders(self, parent_id):
        return [
            folder for folder in self.folders.values() if folder.parent_id == parent_id
        ]

    async def folder_name_exists(self, parent_id, name, exclude_id=None):
        return any(
            folder.parent_id == parent_id
            and folder.name.lower() == name.lower()
            and folder.id != exclude_id
            for folder in self.folders.values()
        )

    async def folder_has_children(self, folder_id):
        has_folders = any(
            folder.parent_id == folder_id for folder in self.folders.values()
        )
        has_files = any(file.folder_id == folder_id for file in self.files.values())
        return has_folders or has_files

    async def get_breadcrumbs(self, folder_id):
        breadcrumbs = []
        current = self.folders.get(folder_id)
        while current:
            breadcrumbs.append(current)
            current = self.folders.get(current.parent_id)
        breadcrumbs.reverse()
        return breadcrumbs

    async def save_file(self, file):
        file.id = str(uuid.uuid4())
        self.files[file.id] = file
        return file

    async def get_file(self, file_id):
        return self.files.get(file_id)

    async def update_file(self, file):
        self.files[file.id] = file
        return file

    async def delete_file(self, file_id):
        return self.files.pop(file_id, None) is not None

    async def list_files(self, folder_id):
        return [file for file in self.files.values() if file.folder_id == folder_id]

    async def file_name_exists(self, folder_id, display_name, exclude_id=None):
        return any(
            file.folder_id == folder_id
            and file.display_name.lower() == display_name.lower()
            and file.id != exclude_id
            for file in self.files.values()
        )


class FakeStorage:
    def __init__(self):
        self.files = {}

    async def save_file(self, file_content, file_name, content_type):
        storage_path = f"library/{uuid.uuid4()}-{file_name}"
        self.files[storage_path] = file_content
        return storage_path

    async def delete_file(self, file_path):
        self.files.pop(file_path, None)
        return True

    async def get_file(self, file_path):
        return self.files[file_path]


@pytest.fixture
def library_fakes(client):
    from main import app

    repo = FakeLibraryRepository()
    storage = FakeStorage()
    app.dependency_overrides[get_library_repository] = lambda: repo
    app.dependency_overrides[get_file_storage_service] = lambda: storage
    yield repo, storage
    app.dependency_overrides.pop(get_library_repository, None)
    app.dependency_overrides.pop(get_file_storage_service, None)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer test-token", "X-User-Role": "admin"}


async def _seed_folder(repo, name="TX", parent_id=None):
    now = datetime.now(timezone.utc)
    folder = LibraryFolder(
        id=str(uuid.uuid4()),
        name=name,
        parent_id=parent_id,
        type="Manual",
        description=None,
        created_by=USER_ID,
        created_at=now,
        updated_at=now,
    )
    repo.folders[folder.id] = folder
    return folder


async def _seed_file(repo, storage, folder_id):
    now = datetime.now(timezone.utc)
    storage_path = "library/seed.pdf"
    storage.files[storage_path] = b"seed manual"
    file = LibraryFile(
        id=str(uuid.uuid4()),
        folder_id=folder_id,
        display_name="TX Manual",
        original_file_name="tx.pdf",
        storage_path=storage_path,
        content_type="application/pdf",
        file_extension="pdf",
        size_bytes=11,
        type="Manual",
        description=None,
        uploaded_by=USER_ID,
        created_at=now,
        updated_at=now,
    )
    repo.files[file.id] = file
    return file


def test_regular_user_can_list_read_and_download(client, library_fakes, auth_headers):
    repo, storage = library_fakes
    folder = client.post(
        "/api/v1/library/folders",
        json={"name": "TX", "type": "Manual"},
        headers={"Authorization": "Bearer test-token", "X-User-Role": "admin"},
    ).json()
    file_response = client.post(
        "/api/v1/library/files/upload",
        data={"folder_id": folder["id"], "type": "Manual", "display_name": "TX Manual"},
        files={"file": ("tx.pdf", b"manual bytes", "application/pdf")},
        headers={"Authorization": "Bearer test-token", "X-User-Role": "admin"},
    )
    assert file_response.status_code == 201
    file_id = file_response.json()["id"]

    root_response = client.get("/api/v1/library/items", headers=auth_headers)
    assert root_response.status_code == 200
    assert root_response.json()["items"][0]["kind"] == "folder"

    folder_response = client.get(
        f"/api/v1/library/items?folder_id={folder['id']}",
        headers=auth_headers,
    )
    assert folder_response.status_code == 200
    assert folder_response.json()["items"][0]["kind"] == "file"

    detail_response = client.get(
        f"/api/v1/library/files/{file_id}", headers=auth_headers
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["display_name"] == "TX Manual"

    download_response = client.get(
        f"/api/v1/library/files/{file_id}/download",
        headers=auth_headers,
    )
    assert download_response.status_code == 200
    assert download_response.content == b"manual bytes"
    assert repo.files[file_id].storage_path in storage.files


def test_regular_user_cannot_write(client, library_fakes, auth_headers):
    response = client.post(
        "/api/v1/library/folders",
        json={"name": "TX", "type": "Manual"},
        headers=auth_headers,
    )

    assert response.status_code == 403


def test_admin_can_create_update_and_delete_folder_and_file(
    client, library_fakes, admin_headers
):
    folder_response = client.post(
        "/api/v1/library/folders",
        json={"name": "TX", "type": "Manual", "description": "TX docs"},
        headers=admin_headers,
    )
    assert folder_response.status_code == 201
    folder_id = folder_response.json()["id"]

    upload_response = client.post(
        "/api/v1/library/files/upload",
        data={"folder_id": folder_id, "type": "Manual", "display_name": "TX Manual"},
        files={"file": ("tx.pdf", b"manual bytes", "application/pdf")},
        headers=admin_headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    update_file_response = client.patch(
        f"/api/v1/library/files/{file_id}",
        json={"display_name": "TX Install Manual"},
        headers=admin_headers,
    )
    assert update_file_response.status_code == 200
    assert update_file_response.json()["display_name"] == "TX Install Manual"

    delete_file_response = client.delete(
        f"/api/v1/library/files/{file_id}",
        headers=admin_headers,
    )
    assert delete_file_response.status_code == 200

    update_folder_response = client.patch(
        f"/api/v1/library/folders/{folder_id}",
        json={"name": "TX Manuals"},
        headers=admin_headers,
    )
    assert update_folder_response.status_code == 200
    assert update_folder_response.json()["name"] == "TX Manuals"

    delete_folder_response = client.delete(
        f"/api/v1/library/folders/{folder_id}",
        headers=admin_headers,
    )
    assert delete_folder_response.status_code == 200


def test_missing_and_non_empty_folder_errors(client, library_fakes, admin_headers):
    folder_response = client.post(
        "/api/v1/library/folders",
        json={"name": "TX", "type": "Manual"},
        headers=admin_headers,
    )
    folder_id = folder_response.json()["id"]
    upload_response = client.post(
        "/api/v1/library/files/upload",
        data={"folder_id": folder_id, "type": "Manual", "display_name": "TX Manual"},
        files={"file": ("tx.pdf", b"manual bytes", "application/pdf")},
        headers=admin_headers,
    )
    assert upload_response.status_code == 201

    missing_response = client.get(
        "/api/v1/library/folders/00000000-0000-0000-0000-000000000000",
        headers=admin_headers,
    )
    assert missing_response.status_code == 404

    delete_response = client.delete(
        f"/api/v1/library/folders/{folder_id}",
        headers=admin_headers,
    )
    assert delete_response.status_code == 400
