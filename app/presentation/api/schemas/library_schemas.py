from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LibraryFolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[str] = None
    type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class LibraryFolderUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class LibraryFileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class LibraryFolderResponse(BaseModel):
    id: str
    name: str
    parent_id: Optional[str]
    type: str
    description: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LibraryFileResponse(BaseModel):
    id: str
    folder_id: str
    display_name: str
    original_file_name: str
    content_type: str
    file_extension: str
    size_bytes: int
    type: str
    description: Optional[str]
    uploaded_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LibraryItemResponse(BaseModel):
    id: str
    kind: str
    name: str
    type: str
    size_bytes: int
    item_count: Optional[int] = Field(
        None,
        description=(
            "Direct child count for folder items; null for files. Counts immediate "
            "subfolders and files only."
        ),
    )
    created_at: datetime
    updated_at: datetime


class LibraryItemsResponse(BaseModel):
    folder: Optional[LibraryFolderResponse]
    breadcrumbs: List[LibraryFolderResponse]
    items: List[LibraryItemResponse]
    total: int


class LibraryDeleteResponse(BaseModel):
    message: str
    id: str
