from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings


class SemanticTextChunkerService:

    def __init__(
        self,
        embeddings: OpenAIEmbeddings,
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: float = 95.0,
        min_chunk_size: int = 100,
    ):
        self.min_chunk_size = min_chunk_size
        self.chunker = SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

    def chunk_text(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        if len(text.strip()) < self.min_chunk_size:
            return [text]

        return self.chunker.split_text(text)
