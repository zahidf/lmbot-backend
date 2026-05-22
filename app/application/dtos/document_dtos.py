from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any


@dataclass
class DocumentUploadDTO:
    """Input DTO for document upload"""

    file: Any  # FastAPI UploadFile
    title: str
    product_series: Optional[str]
    category: Optional[str]
    uploaded_by: str


@dataclass
class DocumentUploadResponseDTO:
    """Output DTO for document upload"""

    id: str
    title: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    product_series: Optional[str]
    category: Optional[str]
    is_processed: bool
    chunk_count: int
    created_at: datetime


@dataclass
class DocumentListDTO:
    """DTO for listing documents"""

    id: str
    title: str
    file_name: str
    file_type: str
    file_size: int
    product_series: Optional[str]
    category: Optional[str]
    is_processed: bool
    created_at: datetime
