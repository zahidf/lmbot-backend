from datetime import datetime, timezone

from app.application.dtos.library_dtos import LibraryUpdateFileDTO
from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.application.use_cases.library._helpers import clean_name
from app.domain.entities.library_file import LibraryFile


class UpdateLibraryFile:
    def __init__(self, library_repository: LibraryRepository):
        self.library_repository = library_repository

    async def execute(self, dto: LibraryUpdateFileDTO) -> LibraryFile:
        """Update file display metadata."""
        file = await self.library_repository.get_file(dto.file_id)
        if not file:
            raise ValueError("File not found")

        if dto.display_name is not None:
            display_name = clean_name(dto.display_name, "display_name")
            if await self.library_repository.file_name_exists(
                file.folder_id,
                display_name,
                exclude_id=file.id,
            ):
                raise ValueError(
                    "A file with this display name already exists in this folder"
                )
            file.display_name = display_name

        file.update_metadata(
            type=clean_name(dto.type, "type") if dto.type is not None else None,
            description=dto.description,
        )
        file.updated_at = datetime.now(timezone.utc)
        return await self.library_repository.update_file(file)
