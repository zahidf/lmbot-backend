from app.application.dtos.library_dtos import LibraryFileDownloadDTO
from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.application.interfaces.services.file_storage_service import FileStorageService


class DownloadLibraryFile:
    def __init__(
        self,
        library_repository: LibraryRepository,
        file_storage_service: FileStorageService,
    ):
        self.library_repository = library_repository
        self.file_storage_service = file_storage_service

    async def execute(self, file_id: str) -> LibraryFileDownloadDTO:
        """Load file metadata and bytes for an authenticated download."""
        file = await self.library_repository.get_file(file_id)
        if not file:
            raise ValueError("File not found")

        content = await self.file_storage_service.get_file(file.storage_path)
        return LibraryFileDownloadDTO(file=file, content=content)
