import pytest
from app.infrastructure.external_services.text_chunking_service import TextChunkerService


class TestTextChunkerService:
    """Test TextChunkerService"""

    @pytest.fixture
    def service(self):
        """Create service with default settings"""
        return TextChunkerService()

    @pytest.fixture
    def custom_service(self):
        """Create service with custom chunk settings"""
        return TextChunkerService(chunk_size=500, chunk_overlap=100)

    def test_chunk_text_basic(self, service):
        """Test basic text chunking"""
        # Arrange
        text = "This is a test sentence. " * 100

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk) <= 1000 for chunk in chunks)  # Default chunk_size

    def test_chunk_text_short_text(self, service):
        """Test chunking text shorter than chunk size"""
        # Arrange
        text = "This is a short text."

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_empty_string(self, service):
        """Test chunking empty string"""
        # Arrange
        text = ""

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert chunks == []

    def test_chunk_text_respects_paragraph_boundaries(self, service):
        """Test that chunking prefers paragraph boundaries"""
        # Arrange
        paragraph1 = "First paragraph content. " * 20
        paragraph2 = "Second paragraph content. " * 20
        text = f"{paragraph1}\n\n{paragraph2}"

        # Act
        chunks = service.chunk_text(text)

        # Assert
        # Chunks should try to break at paragraph boundaries
        assert len(chunks) >= 2

    def test_chunk_text_respects_sentence_boundaries(self, service):
        """Test that chunking prefers sentence boundaries"""
        # Arrange
        text = "Sentence one. Sentence two. Sentence three. " * 30

        # Act
        chunks = service.chunk_text(text)

        # Assert
        # Most chunks should end with a period (sentence boundary)
        chunks_ending_with_period = sum(1 for c in chunks if c.rstrip().endswith('.'))
        assert chunks_ending_with_period >= len(chunks) // 2

    def test_chunk_text_with_custom_settings(self, custom_service):
        """Test chunking with custom chunk size"""
        # Arrange
        text = "Word " * 200  # 1000 chars

        # Act
        chunks = custom_service.chunk_text(text)

        # Assert
        assert len(chunks) > 1
        # With 500 char chunks, we should get at least 2 chunks for 1000 chars
        assert all(len(chunk) <= 500 for chunk in chunks)

    def test_chunk_overlap(self, custom_service):
        """Test that consecutive chunks actually share overlapping content"""
        # Arrange - create text with unique markers
        paragraphs = [f"Paragraph {i}. Unique content for paragraph {i}. " * 10 
                    for i in range(5)]
        text = "\n\n".join(paragraphs)
        
        # Act
        chunks = custom_service.chunk_text(text)

        assert len(chunks) >= 2
        
        # if we have enough chunks
        if len(chunks) >= 2:
            # Check if chunks actually overlap by looking at endings/beginnings
            for i in range(len(chunks) - 1):
                chunk_end = chunks[i][-100:]  # Last 100 chars of chunk i
                chunk_start = chunks[i + 1][:100]  # First 100 chars of chunk i+1
                
                # Calculate overlap percentage
                overlap_words = set(chunk_end.split()) & set(chunk_start.split())
                
                # Assert there's significant overlap
                assert len(overlap_words) > 2, \
                    f"Chunks {i} and {i+1} don't have meaningful overlap"
    

    def test_chunk_text_whitespace_only(self, service):
        """Test chunking whitespace-only text"""
        # Arrange
        text = "   \n\n\t\t   "

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert chunks == [] or all(c.strip() == '' for c in chunks)

    def test_chunk_text_unicode(self, service):
        """Test chunking text with unicode characters"""
        # Arrange
        text = "日本語のテキスト。" * 200  # Japanese text

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert len(chunks) >= 1
        # Verify unicode is preserved
        assert any("日本語" in chunk for chunk in chunks)

    def test_chunk_text_mixed_newlines(self, service):
        """Test chunking with mixed newline styles"""
        # Arrange
        text = "Line 1.\r\nLine 2.\nLine 3.\r\n\r\nParagraph 2." * 50

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert len(chunks) >= 1
        # Text should be processed without errors

    def test_chunk_text_very_long_word(self, service):
        """Test chunking with a very long word"""
        # Arrange
        long_word = "a" * 500
        text = f"Normal text. {long_word} More normal text."

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert len(chunks) >= 1
        # The long word should be preserved somewhere
        full_text = "".join(chunks)
        assert long_word in full_text or len(long_word) > 1000  # Either preserved or too long

    def test_chunk_text_large_document(self, service):
        """Test chunking a large document"""
        # Arrange
        text = "This is content for a large document. " * 1000  # ~38000 chars

        # Act
        chunks = service.chunk_text(text)

        # Assert
        assert len(chunks) > 30  # Should have many chunks
        assert all(len(chunk) <= 1000 for chunk in chunks)

    def test_default_settings(self):
        """Test service uses correct default settings"""
        # Arrange & Act
        service = TextChunkerService()

        # Assert - verify splitter was configured correctly
        assert service.text_splitter._chunk_size == 1000
        assert service.text_splitter._chunk_overlap == 200

    def test_custom_settings(self):
        """Test service accepts custom settings"""
        # Arrange & Act
        service = TextChunkerService(chunk_size=2000, chunk_overlap=400)

        # Assert
        assert service.text_splitter._chunk_size == 2000
        assert service.text_splitter._chunk_overlap == 400

    def test_chunk_text_returns_list(self, service):
        """Test that chunk_text always returns a list"""
        # Arrange
        texts = [
            "Short text",
            "Longer text " * 500,
            "",
            "   ",
        ]

        # Act & Assert
        for text in texts:
            result = service.chunk_text(text)
            assert isinstance(result, list)
