from datetime import datetime, timezone

from app.application.dtos.library_dtos import LibraryCreateFolderDTO
from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.application.use_cases.library._helpers import clean_name
from app.domain.entities.library_folder import LibraryFolder


class CreateLibraryFolder:
    def __init__(self, library_repository: LibraryRepository):
        self.library_repository = library_repository

    async def execute(self, dto: LibraryCreateFolderDTO) -> LibraryFolder:
        """Create a folder under the requested parent or at the root."""
        name = clean_name(dto.name)
        folder_type = clean_name(dto.type, "type")

        if dto.parent_id:
            parent = await self.library_repository.get_folder(dto.parent_id)
            if not parent:
                raise ValueError("Parent folder not found")

        if await self.library_repository.folder_name_exists(dto.parent_id, name):
            raise ValueError("A folder with this name already exists in this location")

        now = datetime.now(timezone.utc)
        folder = LibraryFolder(
            id=None,
            name=name,
            parent_id=dto.parent_id,
            type=folder_type,
            description=dto.description,
            created_by=dto.created_by,
            created_at=now,
            updated_at=now,
        )
        return await self.library_repository.save_folder(folder)
