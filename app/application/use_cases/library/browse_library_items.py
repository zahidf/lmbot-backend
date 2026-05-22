from app.application.dtos.library_dtos import (
    LibraryBrowseDTO,
    LibraryBrowseResponseDTO,
    LibraryItemDTO,
)
from app.application.interfaces.repositories.library_repository import LibraryRepository
from app.application.use_cases.library._helpers import type_matches
from app.domain.entities.library_file import LibraryFile
from app.domain.entities.library_folder import LibraryFolder


class BrowseLibraryItems:
    def __init__(self, library_repository: LibraryRepository):
        self.library_repository = library_repository

    async def execute(self, dto: LibraryBrowseDTO) -> LibraryBrowseResponseDTO:
        """Return folders and files for one library folder."""
        current_folder = None
        breadcrumbs: list[LibraryFolder] = []

        if dto.folder_id:
            current_folder = await self.library_repository.get_folder(dto.folder_id)
            if not current_folder:
                raise ValueError("Folder not found")
            breadcrumbs = await self.library_repository.get_breadcrumbs(dto.folder_id)

        folders = await self.library_repository.list_folders(dto.folder_id)
        files = await self._list_files(dto.folder_id)

        items = [
            await self._folder_item(folder)
            for folder in folders
            if self._include_folder(folder, dto.search, dto.type)
        ]
        items.extend(
            self._file_item(file)
            for file in files
            if self._include_file(file, dto.search, dto.type)
        )

        self._sort_items(items, dto.date, dto.size)
        total = len(items)
        return LibraryBrowseResponseDTO(
            folder=current_folder,
            breadcrumbs=breadcrumbs,
            items=items[dto.offset : dto.offset + dto.limit],
            total=total,
        )

    async def _list_files(self, folder_id: str | None) -> list[LibraryFile]:
        if folder_id is None:
            return []
        return await self.library_repository.list_files(folder_id)

    async def _folder_item(self, folder: LibraryFolder) -> LibraryItemDTO:
        files = await self.library_repository.list_files(folder.id or "")
        size_bytes = sum(file.size_bytes for file in files)
        return LibraryItemDTO(
            id=folder.id or "",
            kind="folder",
            name=folder.name,
            type=folder.type,
            size_bytes=size_bytes,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )

    def _file_item(self, file: LibraryFile) -> LibraryItemDTO:
        return LibraryItemDTO(
            id=file.id or "",
            kind="file",
            name=file.display_name,
            type=file.type,
            size_bytes=file.size_bytes,
            created_at=file.created_at,
            updated_at=file.updated_at,
        )

    def _include_folder(
        self,
        folder: LibraryFolder,
        search: str | None,
        requested_type: str | None,
    ) -> bool:
        return self._matches_search(folder.name, search) and type_matches(
            folder.type,
            requested_type,
        )

    def _include_file(
        self,
        file: LibraryFile,
        search: str | None,
        requested_type: str | None,
    ) -> bool:
        return self._matches_search(file.display_name, search) and type_matches(
            file.type,
            requested_type,
        )

    def _matches_search(self, value: str, search: str | None) -> bool:
        if not search:
            return True
        return search.strip().lower() in value.lower()

    def _sort_items(
        self,
        items: list[LibraryItemDTO],
        date: str | None,
        size: str | None,
    ) -> None:
        if size == "largest":
            items.sort(key=lambda item: item.size_bytes, reverse=True)
            return
        if size == "smallest":
            items.sort(key=lambda item: item.size_bytes)
            return
        if date == "oldest":
            items.sort(key=lambda item: item.created_at)
            return
        items.sort(key=lambda item: item.created_at, reverse=True)
