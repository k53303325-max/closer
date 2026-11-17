"""Stage 3: invites and signatures

Revision ID: 20261116_0003
Revises: 20261108_0002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261116_0003"
down_revision: Union[str, None] = "20261108_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("counterparty_user_id", sa.Integer(), sa.ForeignKey("users.id")))
    op.add_column("documents", sa.Column("invite_token_hash", sa.String(64), unique=True))
    op.add_column("documents", sa.Column("invite_expires_at", sa.DateTime(timezone=True)))
    op.add_column("documents", sa.Column("change_request", sa.JSON(), server_default="{}"))

    op.create_table(
        "signatures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("pdf_sha256", sa.String(64)),
        sa.Column("otp_hash", sa.String(64)),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True)),
        sa.Column("otp_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("otp_locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_code_sent_at", sa.DateTime(timezone=True)),
        sa.Column("sms_sent_count", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("document_id", "version_no", "user_id", name="uq_sign_doc_ver_user"),
    )
    op.create_index("ix_signatures_document_id", "signatures", ["document_id"])


def downgrade() -> None:
    op.drop_table("signatures")
    op.drop_column("documents", "change_request")
    op.drop_column("documents", "invite_expires_at")
    op.drop_column("documents", "invite_token_hash")
    op.drop_column("documents", "counterparty_user_id")