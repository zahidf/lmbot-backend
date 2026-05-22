from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.library_file import LibraryFile
from app.domain.entities.library_folder import LibraryFolder


class LibraryRepository(ABC):
    @abstractmethod
    async def save_folder(self, folder: LibraryFolder) -> LibraryFolder:
        pass

    @abstractmethod
    async def get_folder(self, folder_id: str) -> Optional[LibraryFolder]:
        pass

    @abstractmethod
    async def update_folder(self, folder: LibraryFolder) -> LibraryFolder:
        pass

    @abstractmethod
    async def delete_folder(self, folder_id: str) -> bool:
        pass

    @abstractmethod
    async def list_folders(self, parent_id: Optional[str]) -> List[LibraryFolder]:
        pass

    @abstractmethod
    async def folder_name_exists(
        self,
        parent_id: Optional[str],
        name: str,
        exclude_id: Optional[str] = None,
    ) -> bool:
        pass

    @abstractmethod
    async def folder_has_children(self, folder_id: str) -> bool:
        pass

    @abstractmethod
    async def get_breadcrumbs(self, folder_id: str) -> List[LibraryFolder]:
        pass

    @abstractmethod
    async def save_file(self, file: LibraryFile) -> LibraryFile:
        pass

    @abstractmethod
    async def get_file(self, file_id: str) -> Optional[LibraryFile]:
        pass

    @abstractmethod
    async def update_file(self, file: LibraryFile) -> LibraryFile:
        pass

    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        pass

    @abstractmethod
    async def list_files(self, folder_id: str) -> List[LibraryFile]:
        pass

    @abstractmethod
    async def file_name_exists(
        self,
        folder_id: str,
        display_name: str,
        exclude_id: Optional[str] = None,
    ) -> bool:
        pass
