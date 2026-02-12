from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ChatMessage:
    """Chat message entity representing a Q&A interaction"""
    
    id: Optional[str]
    user_id: str
    session_id: str
    query: str
    response: str
    source_document_ids: List[str]
    created_at: datetime
    
    def has_sources(self) -> bool:
        """Check if message has source documents"""
        return len(self.source_document_ids) > 0