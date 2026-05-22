from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DocumentUpload:
    """Document upload entity"""

    ALLOWED_FILE_TYPES = ["pdf", "docx", "doc", "txt"]

    MAX_FILE_SIZE = 50 * 1024 * 1024

    id: Optional[str]
    title: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    product_series: Optional[str]
    category: Optional[str]
    uploaded_by: str
    is_processed: bool
    chunk_count: int
    created_at: datetime

    def is_valid_file_type(self) -> bool:
        """Check if file type is allowed"""
        return self.file_type.lower() in self.ALLOWED_FILE_TYPES

    def is_valid_file_size(self) -> bool:
        """Check if file size is within limits"""
        return self.file_size <= self.MAX_FILE_SIZE

    def mark_as_processed(self, chunk_count: int) -> None:
        """Mark document as processed"""
        self.is_processed = True
        self.chunk_count = chunk_count
