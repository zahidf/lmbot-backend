import asyncio
from sqlalchemy import select
from app.infrastructure.persistence.database import async_session_factory
from app.infrastructure.persistence.models.document_model import DocumentModel
from app.application.use_cases.documents.process_document import ProcessDocument


class DocumentProcessingWorker:
    """Background worker to process uploaded documents"""

    def __init__(self, process_document_use_case: ProcessDocument):
        self.process_document = process_document_use_case

    async def process_pending_documents(self):
        """Process all unprocessed documents"""

        async with async_session_factory() as session:
            # Get unprocessed documents
            result = await session.execute(
                select(DocumentModel)
                .where(DocumentModel.is_processed == False)
                .order_by(DocumentModel.created_at)
            )

            documents = result.scalars().all()

            for doc in documents:
                try:
                    print(f"Processing document: {doc.title}")
                    result = await self.process_document.execute(str(doc.id))
                    print(f"✅ Processed: {result['chunk_count']} chunks")

                except Exception as e:
                    print(f"❌ Error processing {doc.title}: {e}")
                    # TODO: mark docs as errored

    async def run_continuously(self, interval: int = 60):
        """Run worker continuously"""
        while True:
            await self.process_pending_documents()
            await asyncio.sleep(interval)  # Check every 60 seconds
