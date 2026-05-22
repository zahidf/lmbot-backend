from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LibraryFile:
    ALLOWED_FILE_EXTENSIONS = ["pdf", "docx", "doc", "txt"]
    MAX_FILE_SIZE = 50 * 1024 * 1024

    id: Optional[str]
    folder_id: str
    display_name: str
    original_file_name: str
    storage_path: str
    content_type: str
    file_extension: str
    size_bytes: int
    type: str
    description: Optional[str]
    uploaded_by: str
    created_at: datetime
    updated_at: datetime

    def is_valid_file_type(self) -> bool:
        return self.file_extension.lower() in self.ALLOWED_FILE_EXTENSIONS

    def is_valid_file_size(self) -> bool:
        return self.size_bytes <= self.MAX_FILE_SIZE

    def update_metadata(
        self,
        display_name: Optional[str] = None,
        type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        if display_name is not None:
            self.display_name = display_name.strip()
        if type is not None:
            self.type = type.strip()
        if description is not None:
            self.description = description
