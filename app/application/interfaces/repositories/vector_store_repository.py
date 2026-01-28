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