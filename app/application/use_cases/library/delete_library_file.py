from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.application.interfaces.services.file_storage_service import FileStorageService


class DeleteLibraryFile:
    def __init__(
        self,
        library_repository: LibraryRepository,
        file_storage_service: FileStorageService,
    ):
        self.library_repository = library_repository
        self.file_storage_service = file_storage_service

    async def execute(self, file_id: str) -> str:
        """Delete file metadata and its stored blob."""
        file = await self.library_repository.get_file(file_id)
        if not file:
            raise ValueError("File not found")

        await self.file_storage_service.delete_file(file.storage_path)
        deleted = await self.library_repository.delete_file(file_id)
        if not deleted:
            raise ValueError("File not found")
        return file_id
