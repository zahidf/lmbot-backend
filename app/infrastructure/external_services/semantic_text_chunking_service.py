from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class SemanticTextChunkerService:

    def __init__(
        self,
        embeddings: OpenAIEmbeddings,
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: float = 80.0,
        min_chunk_size: int = 500,
        max_chunk_size: int = 1500,
        chunk_overlap: int = 200,
    ):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        if len(text.strip()) < self.min_chunk_size:
            return [text]

        raw_chunks = self.chunker.split_text(text)

        # Split large chunks
        split_chunks = []
        for chunk in raw_chunks:
            if len(chunk) > self.max_chunk_size:
                split_chunks.extend(self.fallback_splitter.split_text(chunk))
            else:
                split_chunks.append(chunk)

        # Filter small chunks
        filtered_chunks = [
            c for c in split_chunks if len(c.strip()) >= self.min_chunk_size
        ]

        # Overlap adjacent chunks
        if self.chunk_overlap > 0 and len(filtered_chunks) > 1:
            filtered_chunks = self._add_overlap(filtered_chunks)

        return filtered_chunks

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        overlapped = []
        for i, chunk in enumerate(chunks):
            prefix = ""
            suffix = ""
            if i > 0:
                prefix = chunks[i - 1][-self.chunk_overlap :]
            if i < len(chunks) - 1:
                suffix = chunks[i + 1][: self.chunk_overlap]
            overlapped.append(prefix + chunk + suffix)
        return overlapped
