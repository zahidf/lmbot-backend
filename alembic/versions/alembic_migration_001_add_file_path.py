"""add file_path column to documents table

Revision ID: 001_add_file_path
Revises:
Create Date: 2026-01-29

This migration adds the file_path column to store the absolute path
to uploaded document files on the server filesystem.
"""

from alembic import op
import sqlalchemy as sa

revision = "001_add_file_path"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add file_path column to documents table"""

    op.add_column(
        "documents", sa.Column("file_path", sa.String(length=500), nullable=True)
    )

    op.execute("""
        UPDATE documents 
        SET file_path = '/uploads/' || file_name
        WHERE file_path IS NULL
    """)

    op.alter_column("documents", "file_path", nullable=False)


def downgrade():
    """Remove file_path column from documents table"""
    op.drop_column("documents", "file_path")
