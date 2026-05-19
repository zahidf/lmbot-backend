from abc import ABC, abstractmethod
from typing import AsyncIterator, List


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

    @abstractmethod
    async def stream_response(
        self,
        query: str,
        context_documents: List[str]
    ) -> AsyncIterator[str]:
        """Stream response tokens using RAG"""
        pass

    @abstractmethod
    async def generate_summary(self, messages: List[dict]) -> str:
        """Generate a concise 2–3 sentence summary of a chat session.
        Each dict has keys: 'query' (str), 'response' (str)."""
        pass