"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bearer_token_hash", sa.String(length=255), nullable=False),
        sa.Column("bearer_token_prefix", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("token_balance", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clients_bearer_token_prefix", "clients", ["bearer_token_prefix"], unique=False)
    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("diagram_storage_path", sa.String(length=512), nullable=False),
        sa.Column("report_storage_path", sa.String(length=512), nullable=True),
        sa.Column("report_schema_version", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("diagram_checksum", sa.String(length=128), nullable=True),
        sa.Column("report_checksum", sa.String(length=128), nullable=True),
        sa.Column("tokens_used", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_client_id", "analysis_jobs", ["client_id"], unique=False)
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_client_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("ix_clients_bearer_token_prefix", table_name="clients")
    op.drop_table("clients")
