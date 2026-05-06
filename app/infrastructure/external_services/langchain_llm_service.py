from typing import List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.application.interfaces.services.llm_service import LLMService


class LangChainLLMService(LLMService):
    """LangChain implementation of LLM service"""

    GAS_SAFETY_KEYWORDS = [
        "commissioning", "gas valve", "gas train", "electrode",
        "pressure test", "leak test", "installation procedure",
        "gas pressure", "pilot gas", "isolat", "gas cock",
        "burner head", "gas supply",
    ]

    GAS_SAFETY_DISCLAIMER = (
        "\n\n⚠ This guidance is for reference by qualified engineers only. "
        "Gas appliance work must be carried out by a Gas Safe registered engineer."
    )

    DISCLAIMER_INDICATORS = ["gas safe", "qualified engineer", "registered engineer"]

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-5-nano",
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
5. SAFETY — REGULATED GAS WORK:
   Certain tasks (commissioning, installation, gas train adjustments, gas valve
   settings, pressure testing, leak testing, electrode replacement) are legally
   restricted to Gas Safe / ACS registered engineers in the UK and equivalently
   qualified personnel elsewhere. When your response covers any of these tasks:
   a) State clearly that the work MUST be carried out by a qualified Gas Safe
      registered engineer
   b) Frame procedures as reference information for qualified personnel, not as
      DIY instructions
   c) Include this disclaimer at the END of the response:
      "⚠ This guidance is for reference by qualified engineers only. Gas
      appliance work must be carried out by a Gas Safe registered engineer."
   d) Do NOT refuse to answer — the documentation is useful reference material
      for engineers — but always include the qualification requirement

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
        
        response = self._ensure_safety_disclaimer(response)
        return response

    async def generate_summary(self, messages: List[dict]) -> str:
        """Generate a concise 2–3 sentence summary of a chat session for ticket escalation"""
        conversation = "\n".join(
            f"Customer: {m['query']}\nBot: {m['response']}"
            for m in messages
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a technical support assistant. Summarise the following customer support "
             "conversation in 2–3 concise sentences, focusing on the customer's issue and what "
             "the bot was unable to resolve. Be brief and factual."),
            ("human", "{conversation}")
        ])

        chain = prompt | self.llm | StrOutputParser()
        return await chain.ainvoke({"conversation": conversation})

    def _ensure_safety_disclaimer(self, response: str) -> str:
        """
        Deterministic fallback that appends a gas safety disclaimer
        if the response covers regulated work but the LLM omitted it.
        """
        lower = response.lower()
        has_regulated_content = any(kw in lower for kw in self.GAS_SAFETY_KEYWORDS)
        if not has_regulated_content:
            return response
        has_disclaimer = any(ind in lower for ind in self.DISCLAIMER_INDICATORS)
        if has_disclaimer:
            return response
        return response + self.GAS_SAFETY_DISCLAIMER