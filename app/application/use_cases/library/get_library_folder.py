from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.domain.entities.library_folder import LibraryFolder


class GetLibraryFolder:
    def __init__(self, library_repository: LibraryRepository):
        self.library_repository = library_repository

    async def execute(self, folder_id: str) -> LibraryFolder:
        """Return one library folder by ID."""
        folder = await self.library_repository.get_folder(folder_id)
        if not folder:
            raise ValueError("Folder not found")
        return folder
