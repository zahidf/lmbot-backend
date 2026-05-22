from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextChunkerService:
    """Split text into chunks for embedding"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks"""
        return self.text_splitter.split_text(text)
