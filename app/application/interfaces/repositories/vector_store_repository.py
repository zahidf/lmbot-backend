from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class VectorStoreRepository(ABC):
    """Interface for vector store operations"""
    
    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query_embedding: Vector embedding of the query
            k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of matching document chunks with metadata
        """
        pass

    @abstractmethod
    async def get_chunks_by_ids(
        self,
        chunk_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Fetch specific chunks by their IDs

        Args:
            chunk_ids: List of chunk UUIDs

        Returns:
            List of chunks with content and metadata, in the same shape as similarity_search results
        """
        pass