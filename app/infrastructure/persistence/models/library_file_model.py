import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class LibraryFileModel(Base):
    __tablename__ = "library_files"
    __table_args__ = (
        Index(
            "uq_library_files_folder_display_name",
            "folder_id",
            text("lower(display_name)"),
            unique=True,
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("library_folders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    display_name = Column(String(255), nullable=False)
    original_file_name = Column(String(500), nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_type = Column(String(255), nullable=False)
    file_extension = Column(String(20), nullable=False, index=True)
    size_bytes = Column(BigInteger, nullable=False)
    type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
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

    folder = relationship("LibraryFolderModel", back_populates="files")
