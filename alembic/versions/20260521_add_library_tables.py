"""add library folder and file tables

Revision ID: 20260521_add_library_tables
Revises: 685dea8b8590
Create Date: 2026-05-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260521_add_library_tables"
down_revision: Union[str, Sequence[str], None] = "685dea8b8590"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "library_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["library_folders.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_library_folders_parent_id",
        "library_folders",
        ["parent_id"],
        unique=False,
    )
    op.create_index(
        "ix_library_folders_type", "library_folders", ["type"], unique=False
    )
    op.create_index(
        "uq_library_folders_root_name",
        "library_folders",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_library_folders_parent_name",
        "library_folders",
        ["parent_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )

    op.create_table(
        "library_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("original_file_name", sa.String(length=500), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["folder_id"], ["library_folders.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_library_files_folder_id", "library_files", ["folder_id"], unique=False
    )
    op.create_index(
        "ix_library_files_file_extension",
        "library_files",
        ["file_extension"],
        unique=False,
    )
    op.create_index("ix_library_files_type", "library_files", ["type"], unique=False)
    op.create_index(
        "uq_library_files_folder_display_name",
        "library_files",
        ["folder_id", sa.text("lower(display_name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_library_files_folder_display_name", table_name="library_files")
    op.drop_index("ix_library_files_type", table_name="library_files")
    op.drop_index("ix_library_files_file_extension", table_name="library_files")
    op.drop_index("ix_library_files_folder_id", table_name="library_files")
    op.drop_table("library_files")

    op.drop_index("uq_library_folders_parent_name", table_name="library_folders")
    op.drop_index("uq_library_folders_root_name", table_name="library_folders")
    op.drop_index("ix_library_folders_type", table_name="library_folders")
    op.drop_index("ix_library_folders_parent_id", table_name="library_folders")
    op.drop_table("library_folders")
