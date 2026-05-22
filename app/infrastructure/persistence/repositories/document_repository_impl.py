from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
import uuid
from app.application.interfaces.repositories.document_repository import (
    DocumentRepository,
)
from app.domain.entities.document_upload import DocumentUpload
from app.infrastructure.persistence.models.document_model import DocumentModel


class DocumentRepositoryImpl(DocumentRepository):
    """PostgreSQL implementation of document repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: DocumentModel, file_size: int) -> DocumentUpload:
        """Convert database model to domain entity"""
        return DocumentUpload(
            id=str(model.id),
            title=model.title,
            file_name=model.file_name,
            file_path=model.file_path,
            file_type=model.file_type,
            file_size=file_size,
            product_series=model.product_series,
            category=model.category,
            uploaded_by=str(model.uploaded_by),
            is_processed=model.is_processed,
            chunk_count=model.chunk_count,
            created_at=model.created_at,
        )

    async def save(self, document: DocumentUpload) -> DocumentUpload:
        """Save document metadata to database (insert or update)"""

        model = DocumentModel(
            id=uuid.UUID(document.id) if document.id else uuid.uuid4(),
            title=document.title,
            file_name=document.file_name,
            file_path=document.file_path,
            file_type=document.file_type,
            product_series=document.product_series,
            category=document.category,
            is_processed=document.is_processed,
            chunk_count=document.chunk_count,
            uploaded_by=uuid.UUID(document.uploaded_by),
            created_at=document.created_at,
        )

        model = await self.session.merge(model)
        await self.session.flush()

        return self._to_entity(model, document.file_size)

    async def find_by_id(self, document_id: str) -> Optional[DocumentUpload]:
        """Find document by ID"""

        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
        )

        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_entity(model, file_size=0)

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        product_series: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[DocumentUpload]:
        """Find all documents with optional filters"""

        query = select(DocumentModel)

        # Apply filters + pagination
        if product_series:
            query = query.where(DocumentModel.product_series == product_series)

        if category:
            query = query.where(DocumentModel.category == category)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model, file_size=0) for model in models]

    async def delete(self, document_id: str) -> bool:
        """Delete document by ID"""

        result = await self.session.execute(
            delete(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
        )

        return result.rowcount > 0
