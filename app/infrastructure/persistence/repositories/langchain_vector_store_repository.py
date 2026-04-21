from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.application.interfaces.repositories.vector_store_repository import VectorStoreRepository


class LangChainVectorStoreRepository(VectorStoreRepository):
    """PostgreSQL + pgvector implementation using LangChain"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity
        
        Args:
            query_embedding: Query vector embedding
            k: Number of results to return
            filters: Optional filters (product_series, category)
            
        Returns:
            List of similar chunks with metadata
        """
        
        # Convert embedding to PostgreSQL array format
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Get asyncpg connection
        raw_connection = await self.session.connection()
        asyncpg_connection = await raw_connection.get_raw_connection()
        
        # Use positional parameters
        query_sql = """
            SELECT 
                id::text as chunk_id,
                document_id::text,
                content,
                chunk_metadata,
                1 - (embedding <=> $1::vector) as similarity_score
            FROM document_chunks
            WHERE 1=1
        """
        
        params = [embedding_str]
        param_counter = 2
        
        # Add filters
        if filters:
            if 'product_series' in filters:
                query_sql += f" AND chunk_metadata->>'product_series' = ${param_counter}"
                params.append(filters['product_series'])
                param_counter += 1
            if 'category' in filters:
                query_sql += f" AND chunk_metadata->>'category' = ${param_counter}"
                params.append(filters['category'])
                param_counter += 1
        
        # Add ordering and limit
        query_sql += f" ORDER BY similarity_score DESC LIMIT ${param_counter}"
        params.append(k)
        
        #execute query and format
        rows = await asyncpg_connection.driver_connection.fetch(query_sql, *params)
        
        results = []
        for row in rows:
            results.append({
                'id': row['chunk_id'],
                'document_id': row['document_id'],
                'content': row['content'],
                'metadata': dict(row['chunk_metadata']) if row['chunk_metadata'] else {},
                'similarity_score': float(row['similarity_score'])
            })
        
        return results
    
    async def get_chunks_by_ids(
        self,
        chunk_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Fetch specific chunks by their chunk IDs"""
        if not chunk_ids:
            return []

        raw_connection = await self.session.connection()
        asyncpg_connection = await raw_connection.get_raw_connection()

        rows = await asyncpg_connection.driver_connection.fetch(
            """
            SELECT
                id::text as chunk_id,
                document_id::text,
                content,
                chunk_metadata
            FROM document_chunks
            WHERE id = ANY($1::uuid[])
            """,
            chunk_ids
        )

        return [
            {
                'id': row['chunk_id'],
                'document_id': row['document_id'],
                'content': row['content'],
                'metadata': dict(row['chunk_metadata']) if row['chunk_metadata'] else {},
                'similarity_score': None
            }
            for row in rows
        ]

    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add documents to the vector store
        
        Args:
            documents: List of documents with content and metadata
            
        Returns:
            List of document IDs
        """
        # This is handled by ProcessDocument use case
        # Kept for interface compatibility
        raise NotImplementedError("Use ProcessDocument use case to add documents")