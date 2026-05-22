from datetime import datetime, timezone
from typing import List, Dict, Any
from app.application.interfaces.repositories.document_repository import (
    DocumentRepository,
)
from app.application.interfaces.services.file_storage_service import FileStorageService
from app.infrastructure.persistence.repositories.langchain_vector_store_repository import (
    LangChainVectorStoreRepository,
)
from app.application.interfaces.services.llm_service import LLMService
from app.infrastructure.external_services.document_processor_service import (
    DocumentProcessorService,
)
from app.infrastructure.external_services.semantic_text_chunking_service import (
    SemanticTextChunkerService,
)
import logging
import uuid

logger = logging.getLogger(__name__)


class ProcessDocument:
    """
    Use Case: Process uploaded document for RAG

    Flow:
    1. Get document metadata from database
    2. Extract text from document file
    3. Split text into chunks
    4. Generate embeddings for each chunk
    5. Store chunks in vector database
    6. Mark document as processed
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_store_repository: LangChainVectorStoreRepository,
        llm_service: LLMService,
        file_storage_service: FileStorageService,
        document_processor: DocumentProcessorService,
        text_chunker: SemanticTextChunkerService,
    ):
        self.document_repository = document_repository
        self.vector_store_repository = vector_store_repository
        self.llm_service = llm_service
        self.file_storage_service = file_storage_service
        self.document_processor = document_processor
        self.text_chunker = text_chunker

    async def execute(self, document_id: str) -> Dict[str, Any]:
        """
        Process document for RAG

        Args:
            document_id: UUID of the document to process

        Returns:
            Dictionary with processing results

        Raises:
            ValueError: If document not found or already processed
            Exception: If processing fails
        """

        # 1. Get document metadata
        document = await self.document_repository.find_by_id(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if document.is_processed:
            return {
                "status": "already_processed",
                "document_id": document_id,
                "chunk_count": document.chunk_count,
            }

        try:
            # 2. Fetch raw bytes then extract text
            file_content = await self.file_storage_service.get_file(document.file_path)
            text = await self.document_processor.extract_text(
                file_content=file_content, file_type=document.file_type
            )

            if not text or len(text.strip()) < 50:
                raise ValueError("Extracted text is too short or empty")

            # 3. Split into chunks
            chunks = self.text_chunker.chunk_text(text)

            if not chunks:
                raise ValueError("No chunks created from text")

            # 4. Process each chunk
            chunk_count = 0
            failed_chunks = []

            for idx, chunk_text in enumerate(chunks):
                try:
                    # Generate embedding
                    embedding = await self.llm_service.generate_embedding(chunk_text)

                    # Prepare metadata
                    chunk_metadata = {
                        "document_id": document_id,
                        "document_title": document.title,
                        "product_series": document.product_series,
                        "category": document.category,
                        "file_name": document.file_name,
                        "file_type": document.file_type,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "chunk_length": len(chunk_text),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }

                    # Store in vector database
                    await self._store_chunk(
                        document_id=document_id,
                        chunk_index=idx,
                        content=chunk_text,
                        embedding=embedding,
                        metadata=chunk_metadata,
                    )

                    chunk_count += 1

                except Exception as e:
                    logger.error(f"Failed to process chunk {idx}: {e}")
                    failed_chunks.append(idx)

            if chunk_count == 0:
                raise ValueError("All chunks failed to process")

            # 5. Mark document as processed
            document.mark_as_processed(chunk_count=chunk_count)
            await self.document_repository.save(document)

            result = {
                "status": "processed",
                "document_id": document_id,
                "chunk_count": chunk_count,
                "failed_chunks": len(failed_chunks),
                "text_length": len(text),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Document processing complete: {result}")
            return result

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            raise

    async def _store_chunk(
        self,
        document_id: str,
        chunk_index: int,
        content: str,
        embedding: List[float],
        metadata: dict,
    ):
        """
        Store chunk in vector database using raw asyncpg

        Args:
            document_id: Parent document UUID
            chunk_index: Index of this chunk
            content: Text content of the chunk
            embedding: Vector embedding
            metadata: Additional metadata
        """
        import json
        from app.infrastructure.persistence.database import async_session_factory

        # Convert embedding list to PostgreSQL array format
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        # Convert metadata to JSON string
        metadata_json = json.dumps(metadata)

        async with async_session_factory() as session:
            raw_connection = await session.connection()
            asyncpg_connection = await raw_connection.get_raw_connection()

            await asyncpg_connection.driver_connection.execute(
                """
                INSERT INTO document_chunks 
                (id, document_id, content, chunk_index, embedding, chunk_metadata, created_at)
                VALUES 
                ($1::uuid, $2::uuid, $3, $4, $5::vector, $6::jsonb, $7::timestamptz)
                """,
                str(uuid.uuid4()),
                document_id,
                content,
                chunk_index,
                embedding_str,
                metadata_json,
                datetime.now(timezone.utc),
            )

            await session.commit()

        logger.debug(f"Stored chunk {chunk_index} in vector database")
