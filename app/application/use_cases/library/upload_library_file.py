from datetime import datetime, timezone

from app.application.dtos.library_dtos import LibraryUploadFileDTO
from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.application.interfaces.services.file_storage_service import FileStorageService
from app.application.use_cases.library._helpers import clean_name
from app.domain.entities.library_file import LibraryFile


class UploadLibraryFile:
    def __init__(
        self,
        library_repository: LibraryRepository,
        file_storage_service: FileStorageService,
    ):
        self.library_repository = library_repository
        self.file_storage_service = file_storage_service

    async def execute(self, dto: LibraryUploadFileDTO) -> LibraryFile:
        """Upload a library file and save its metadata."""
        folder = await self.library_repository.get_folder(dto.folder_id)
        if not folder:
            raise ValueError("Folder not found")

        original_name = dto.file.filename
        display_name = clean_name(dto.display_name or original_name, "display_name")
        file_extension = self._extract_file_extension(original_name)
        size_bytes = await self._file_size(dto.file)

        file = LibraryFile(
            id=None,
            folder_id=dto.folder_id,
            display_name=display_name,
            original_file_name=original_name,
            storage_path="",
            content_type=dto.file.content_type or "application/octet-stream",
            file_extension=file_extension,
            size_bytes=size_bytes,
            type=clean_name(dto.type, "type"),
            description=dto.description,
            uploaded_by=dto.uploaded_by,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        if not file.is_valid_file_type():
            allowed = ", ".join(LibraryFile.ALLOWED_FILE_EXTENSIONS)
            raise ValueError(
                f"Invalid file type: {file_extension}. Allowed types: {allowed}"
            )

        if not file.is_valid_file_size():
            max_size_mb = LibraryFile.MAX_FILE_SIZE // (1024 * 1024)
            raise ValueError(
                f"File size exceeds maximum allowed size of {max_size_mb}MB"
            )

        if await self.library_repository.file_name_exists(dto.folder_id, display_name):
            raise ValueError(
                "A file with this display name already exists in this folder"
            )

        content = await dto.file.read()
        file.storage_path = await self.file_storage_service.save_file(
            file_content=content,
            file_name=original_name,
            content_type=file.content_type,
        )
        return await self.library_repository.save_file(file)

    async def _file_size(self, upload_file) -> int:
        if hasattr(upload_file, "size") and upload_file.size is not None:
            return upload_file.size

        content = await upload_file.read()
        if hasattr(upload_file, "seek"):
            await upload_file.seek(0)
        return len(content)

    def _extract_file_extension(self, file_name: str) -> str:
        return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
