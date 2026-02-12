from typing import List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.application.interfaces.services.llm_service import LLMService


class LangChainLLMService(LLMService):
    """LangChain implementation of LLM service"""
    
    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4",
        embedding_model: str = "text-embedding-3-small",
        temperature: float = 0.7
    ):
        self.openai_api_key = openai_api_key
        self.model_name = model
        self.embedding_model_name = embedding_model
        self.temperature = temperature
        
        self._llm = None
        self._embeddings = None
    
    @property
    def llm(self) -> ChatOpenAI:
        """Lazy load LLM"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                openai_api_key=self.openai_api_key
            )
        return self._llm
    
    @property
    def embeddings(self) -> OpenAIEmbeddings:
        """Lazy load embeddings"""
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                model=self.embedding_model_name,
                openai_api_key=self.openai_api_key
            )
        return self._embeddings
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        embedding = await self.embeddings.aembed_query(text)
        return embedding
    
    async def generate_response(
        self,
        query: str,
        context_documents: List[str]
    ) -> str:
        """Generate response using RAG with LangChain"""
        
        # System prompt
        system_prompt = """You are a technical support assistant for Lanemark Combustion Engineering Limited.

Your role is to help customers with their industrial burner products using the provided documentation.

Guidelines:
1. Answer ONLY based on the provided context documents
2. If the answer is not in the context, say "I don't have enough information to answer that" (NOTHING ELSE)
3. Be specific and reference relevant information
4. Use technical terminology appropriately
5. Provide safety warnings when relevant 

Product Lines:
- TX Series: High-efficiency industrial burners
- FD Series: Forced draft burners
- HC Series: High-capacity burners
- KS Series: Compact burners"""
        
        # Format context
        context = "\n\n".join([
            f"Document {i+1}:\n{doc}"
            for i, doc in enumerate(context_documents)
        ])
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """Context from documentation:
{context}

Customer Question: {query}

Provide a helpful, accurate response based on the documentation.""")
        ])
        
        # Create chain
        chain = prompt | self.llm | StrOutputParser()
        
        # Generate response
        response = await chain.ainvoke({
            "context": context,
            "query": query
        })
        
        return response