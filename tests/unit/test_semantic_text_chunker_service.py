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
        mock_chunker_instance.split_text.return_value = ["chunk one", "chunk two"]
        MockChunker.return_value = mock_chunker_instance

        svc = SemanticTextChunkerService(
            embeddings=mock_embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=95.0,
            min_chunk_size=100,
        )
        yield svc


class TestSemanticTextChunkerService:

    def test_chunk_text_returns_list(self, service):
        result = service.chunk_text("A" * 200)
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
        text = "A" * 200
        service.chunk_text(text)
        service.chunker.split_text.assert_called_once_with(text)

    def test_chunk_text_unicode(self, service):
        text = "日本語のテキスト。" * 50
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
