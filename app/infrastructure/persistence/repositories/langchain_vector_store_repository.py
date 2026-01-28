from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ....application.interfaces.repositories.vector_store_repository import VectorStoreRepository


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
        """
        
        # Convert embedding to string format for PostgreSQL
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Build base query
        base_query = """
            SELECT 
                id::text,
                document_id::text,
                content,
                chunk_metadata,
                1 - (embedding <=> '{embedding}'::vector) as similarity_score
            FROM document_chunks
            WHERE 1=1
        """
        
        # Add filters if provided
        if filters:
            if 'product_series' in filters:
                base_query += f" AND chunk_metadata->>'product_series' = '{filters['product_series']}'"
            if 'category' in filters:
                base_query += f" AND chunk_metadata->>'category' = '{filters['category']}'"
        
        # Add ordering and limit
        base_query += f" ORDER BY similarity_score DESC LIMIT {k}"
        
        # Format query with embedding
        query_sql = base_query.format(embedding=embedding_str)
        
        # Execute query and format results
        result = await self.session.execute(text(query_sql))
        rows = result.fetchall()

        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'document_id': row[1],
                'content': row[2],
                'metadata': row[3] or {},  # Still return as 'metadata' in the dict
                'similarity_score': float(row[4])
            })
        
        return results