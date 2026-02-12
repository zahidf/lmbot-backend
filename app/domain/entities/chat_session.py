from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChatSession:
    """Chat session entity representing a conversation thread"""
    
    id: Optional[str]
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    def update_title(self, title: str) -> None:
        """Update session title"""
        self.title = title[:500] if title else None
    
    @staticmethod
    def generate_title_from_query(query: str) -> str:
        """Generate a session title from the first query"""
        title = query.strip()
        if len(title) > 100:
            title = title[:97] + "..."
        return title