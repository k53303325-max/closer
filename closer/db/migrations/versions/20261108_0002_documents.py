"""Stage 2: documents and document_versions

Revision ID: 20261108_0002
Revises: 20261107_0001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0002"
down_revision: Union[str, None] = "20261107_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_key", sa.String(32), server_default="uslugi", nullable=False),
        sa.Column("status", sa.String(32), server_default="composing", nullable=False),
        sa.Column("contract_number", sa.String(32)),
        sa.Column("user_role", sa.String(16)),
        sa.Column("deal", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_owner_user_id", "documents", ["owner_user_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("values", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("pdf_storage_key", sa.String(512)),
        sa.Column("pdf_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("document_id", "version_no", name="uq_document_version_no"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])


def downgrade() -> None:
    op.drop_table("document_versions")
    op.drop_table("documents")
