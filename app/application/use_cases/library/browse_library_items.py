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
        """Return browsable library items with explicit folder-scoped search."""
        current_folder = None
        breadcrumbs: list[LibraryFolder] = []

        if dto.folder_id:
            current_folder = await self.library_repository.get_folder(dto.folder_id)
            if not current_folder:
                raise ValueError("Folder not found")
            breadcrumbs = await self.library_repository.get_breadcrumbs(dto.folder_id)

        if dto.search:
            folders = await self.library_repository.list_folders_recursive(
                dto.folder_id
            )
            files = await self.library_repository.list_files_recursive(dto.folder_id)
        else:
            folders = await self.library_repository.list_folders(dto.folder_id)
            files = await self._list_files(dto.folder_id)

        folder_ids = [folder.id for folder in folders if folder.id]
        child_counts = await self.library_repository.get_folder_child_counts(folder_ids)
        child_file_sizes = await self.library_repository.get_folder_child_file_sizes(
            folder_ids
        )

        items = [
            self._folder_item(folder, child_counts, child_file_sizes)
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

    def _folder_item(
        self,
        folder: LibraryFolder,
        child_counts: dict[str, int],
        child_file_sizes: dict[str, int],
    ) -> LibraryItemDTO:
        folder_id = folder.id or ""
        return LibraryItemDTO(
            id=folder_id,
            kind="folder",
            name=folder.name,
            type=folder.type,
            size_bytes=child_file_sizes.get(folder_id, 0),
            item_count=child_counts.get(folder_id, 0),
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
            item_count=None,
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
