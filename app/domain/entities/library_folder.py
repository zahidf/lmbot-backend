from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LibraryFolder:
    id: Optional[str]
    name: str
    parent_id: Optional[str]
    type: str
    description: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime

    def rename(self, name: str) -> None:
        self.name = name.strip()

    def update_metadata(
        self,
        type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        if type is not None:
            self.type = type.strip()
        if description is not None:
            self.description = description
