from abc import ABC, abstractmethod
from typing import List


class LLMService(ABC):
    """Interface for Language Model operations"""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        query: str,
        context_documents: List[str]
    ) -> str:
        """Generate response using RAG"""
        pass