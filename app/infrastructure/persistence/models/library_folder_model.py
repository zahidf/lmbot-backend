import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class LibraryFolderModel(Base):
    __tablename__ = "library_folders"
    __table_args__ = (
        Index(
            "uq_library_folders_root_name",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index(
            "uq_library_folders_parent_name",
            "parent_id",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("library_folders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    parent = relationship(
        "LibraryFolderModel", remote_side=[id], back_populates="children"
    )
    children = relationship("LibraryFolderModel", back_populates="parent")
    files = relationship("LibraryFileModel", back_populates="folder")
