from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.document_upload import DocumentUpload


class DocumentRepository(ABC):
    """Interface for document persistence"""
    
    @abstractmethod
    async def save(self, document: DocumentUpload) -> DocumentUpload:
        """Save document metadata"""
        pass
    
    @abstractmethod
    async def find_by_id(self, document_id: str) -> Optional[DocumentUpload]:
        """Find document by ID"""
        pass
    
    @abstractmethod
    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        product_series: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[DocumentUpload]:
        """Find all documents with optional filters"""
        pass
    
    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete document by ID"""
        pass