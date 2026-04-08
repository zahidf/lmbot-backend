import pytest
from unittest.mock import MagicMock, patch
from app.infrastructure.external_services.semantic_text_chunking_service import SemanticTextChunkerService


@pytest.fixture
def mock_embeddings():
    return MagicMock()


@pytest.fixture
def service(mock_embeddings):
    with patch(
        "app.infrastructure.external_services.semantic_text_chunking_service.SemanticChunker"
    ) as MockChunker:
        mock_chunker_instance = MagicMock()
        mock_chunker_instance.split_text.return_value = ["A" * 600, "B" * 600]
        MockChunker.return_value = mock_chunker_instance

        svc = SemanticTextChunkerService(
            embeddings=mock_embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=80.0,
            min_chunk_size=500,
            max_chunk_size=1500,
            chunk_overlap=200,
        )
        yield svc


class TestSemanticTextChunkerService:

    def test_chunk_text_returns_list(self, service):
        result = service.chunk_text("A" * 600)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_chunk_text_empty_string(self, service):
        result = service.chunk_text("")
        assert result == []

    def test_chunk_text_whitespace_only(self, service):
        result = service.chunk_text("   \n\t  ")
        assert result == []

    def test_chunk_text_short_text_below_min(self, service):
        short = "Hello world."
        result = service.chunk_text(short)
        assert result == [short]

    def test_chunk_text_delegates_to_semantic_chunker(self, service):
        text = "A" * 600
        service.chunk_text(text)
        service.chunker.split_text.assert_called_once_with(text)

    def test_chunk_text_unicode(self, service):
        text = "日本語のテキスト。" * 100
        result = service.chunk_text(text)
        assert isinstance(result, list)

    def test_constructor_passes_config(self, mock_embeddings):
        with patch(
            "app.infrastructure.external_services.semantic_text_chunking_service.SemanticChunker"
        ) as MockChunker:
            SemanticTextChunkerService(
                embeddings=mock_embeddings,
                breakpoint_threshold_type="standard_deviation",
                breakpoint_threshold_amount=1.5,
                min_chunk_size=50,
            )
            MockChunker.assert_called_once_with(
                embeddings=mock_embeddings,
                breakpoint_threshold_type="standard_deviation",
                breakpoint_threshold_amount=1.5,
            )

    def test_min_chunk_size_boundary(self, mock_embeddings):
        with patch(
            "app.infrastructure.external_services.semantic_text_chunking_service.SemanticChunker"
        ) as MockChunker:
            mock_instance = MagicMock()
            MockChunker.return_value = mock_instance

            svc = SemanticTextChunkerService(
                embeddings=mock_embeddings,
                min_chunk_size=50,
            )

            exactly_50 = "A" * 50
            svc.chunk_text(exactly_50)
            mock_instance.split_text.assert_called_once_with(exactly_50)

    def test_oversized_chunks_are_split(self, mock_embeddings):
        with patch(
            "app.infrastructure.external_services.semantic_text_chunking_service.SemanticChunker"
        ) as MockChunker:
            mock_instance = MagicMock()
            # Return one chunk that exceeds max_chunk_size
            mock_instance.split_text.return_value = ["A" * 3000]
            MockChunker.return_value = mock_instance

            svc = SemanticTextChunkerService(
                embeddings=mock_embeddings,
                min_chunk_size=100,
                max_chunk_size=1500,
                chunk_overlap=0,
            )

            result = svc.chunk_text("A" * 3000)
            assert len(result) >= 2
            for chunk in result:
                assert len(chunk) <= 1500

    def test_garbage_chunks_are_filtered(self, mock_embeddings):
        with patch(
            "app.infrastructure.external_services.semantic_text_chunking_service.SemanticChunker"
        ) as MockChunker:
            mock_instance = MagicMock()
            mock_instance.split_text.return_value = ["A" * 600, ")", "B" * 600]
            MockChunker.return_value = mock_instance

            svc = SemanticTextChunkerService(
                embeddings=mock_embeddings,
                min_chunk_size=500,
                max_chunk_size=1500,
                chunk_overlap=0,
            )

            result = svc.chunk_text("A" * 600)
            assert ")" not in result
            assert len(result) == 2

    def test_overlap_is_added_between_chunks(self, mock_embeddings):
        with patch(
            "app.infrastructure.external_services.semantic_text_chunking_service.SemanticChunker"
        ) as MockChunker:
            mock_instance = MagicMock()
            chunk_a = "A" * 600
            chunk_b = "B" * 600
            mock_instance.split_text.return_value = [chunk_a, chunk_b]
            MockChunker.return_value = mock_instance

            svc = SemanticTextChunkerService(
                embeddings=mock_embeddings,
                min_chunk_size=500,
                max_chunk_size=1500,
                chunk_overlap=100,
            )

            result = svc.chunk_text("X" * 1200)
            # First chunk should have suffix from second chunk
            assert result[0].endswith("B" * 100)
            # Last chunk should have prefix from first chunk
            assert result[1].startswith("A" * 100)

    def test_no_overlap_when_disabled(self, mock_embeddings):
        with patch(
            "app.infrastructure.external_services.semantic_text_chunking_service.SemanticChunker"
        ) as MockChunker:
            mock_instance = MagicMock()
            chunk_a = "A" * 600
            chunk_b = "B" * 600
            mock_instance.split_text.return_value = [chunk_a, chunk_b]
            MockChunker.return_value = mock_instance

            svc = SemanticTextChunkerService(
                embeddings=mock_embeddings,
                min_chunk_size=500,
                max_chunk_size=1500,
                chunk_overlap=0,
            )

            result = svc.chunk_text("X" * 1200)
            assert result[0] == chunk_a
            assert result[1] == chunk_b
