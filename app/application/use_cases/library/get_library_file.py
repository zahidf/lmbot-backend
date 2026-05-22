from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.domain.entities.library_file import LibraryFile


class GetLibraryFile:
    def __init__(self, library_repository: LibraryRepository):
        self.library_repository = library_repository

    async def execute(self, file_id: str) -> LibraryFile:
        """Return one library file by ID."""
        file = await self.library_repository.get_file(file_id)
        if not file:
            raise ValueError("File not found")
        return file
