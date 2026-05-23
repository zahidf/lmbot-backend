from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from app.domain.entities.library_file import LibraryFile
from app.domain.entities.library_folder import LibraryFolder


@dataclass
class LibraryItemDTO:
    id: str
    kind: str
    name: str
    type: str
    size_bytes: int
    item_count: Optional[int]
    created_at: datetime
    updated_at: datetime


@dataclass
class LibraryBrowseDTO:
    folder_id: Optional[str]
    search: Optional[str]
    type: Optional[str]
    date: Optional[str]
    size: Optional[str]
    limit: int
    offset: int


@dataclass
class LibraryBrowseResponseDTO:
    folder: Optional[LibraryFolder]
    breadcrumbs: List[LibraryFolder]
    items: List[LibraryItemDTO]
    total: int


@dataclass
class LibraryCreateFolderDTO:
    name: str
    parent_id: Optional[str]
    type: str
    description: Optional[str]
    created_by: str


@dataclass
class LibraryUpdateFolderDTO:
    folder_id: str
    name: Optional[str]
    type: Optional[str]
    description: Optional[str]


@dataclass
class LibraryUploadFileDTO:
    file: Any
    folder_id: str
    type: str
    display_name: Optional[str]
    description: Optional[str]
    uploaded_by: str


@dataclass
class LibraryUpdateFileDTO:
    file_id: str
    display_name: Optional[str]
    type: Optional[str]
    description: Optional[str]


@dataclass
class LibraryFileDownloadDTO:
    file: LibraryFile
    content: bytes
