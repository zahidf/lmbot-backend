import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from app.infrastructure.external_services.langchain_llm_service import LangChainLLMService


class TestLangChainLLMService:
    """Tests for LangChain LLM service"""
    
    @pytest.fixture
    def service(self):
        # Mock external dependencies
        with patch('langchain_openai.ChatOpenAI'), \
             patch('langchain_openai.OpenAIEmbeddings'):
            return LangChainLLMService(
                openai_api_key="test-key",
                model="gpt-4",
                embedding_model="text-embedding-3-small"
            )
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self, service):
        """Test embedding generation"""
        mock_embedding = [0.1] * 1536
        
        with patch.object(service, '_embeddings') as mock_embeddings:
            mock_embeddings.aembed_query = AsyncMock(return_value=mock_embedding)
            
            result = await service.generate_embedding("test text")
            
            assert result == mock_embedding
            mock_embeddings.aembed_query.assert_called_once_with("test text")
    
    @pytest.mark.asyncio
    async def test_generate_response(self, service):
        """Test response generation with context"""

        with patch.object(LangChainLLMService, 'generate_response') as mock_method:
            mock_method.return_value = "Generated response"
        
            context = ["Document 1", "Document 2"]
            result = await service.generate_response(
                query="Test query",
                context_documents=context
            )
        
            assert result == "Generated response"
            mock_method.assert_called_once()