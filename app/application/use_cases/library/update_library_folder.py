from datetime import datetime, timezone

from app.application.dtos.library_dtos import LibraryUpdateFolderDTO
from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.application.use_cases.library._helpers import clean_name
from app.domain.entities.library_folder import LibraryFolder


class UpdateLibraryFolder:
    def __init__(self, library_repository: LibraryRepository):
        self.library_repository = library_repository

    async def execute(self, dto: LibraryUpdateFolderDTO) -> LibraryFolder:
        """Update folder display metadata."""
        folder = await self.library_repository.get_folder(dto.folder_id)
        if not folder:
            raise ValueError("Folder not found")

        if dto.name is not None:
            name = clean_name(dto.name)
            if await self.library_repository.folder_name_exists(
                folder.parent_id,
                name,
                exclude_id=folder.id,
            ):
                raise ValueError(
                    "A folder with this name already exists in this location"
                )
            folder.rename(name)

        folder.update_metadata(
            type=clean_name(dto.type, "type") if dto.type is not None else None,
            description=dto.description,
        )
        folder.updated_at = datetime.now(timezone.utc)
        return await self.library_repository.update_folder(folder)
