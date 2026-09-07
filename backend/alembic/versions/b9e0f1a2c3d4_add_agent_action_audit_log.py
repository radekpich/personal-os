"""add agent action audit log

Revision ID: b9e0f1a2c3d4
Revises: a8d9e0f1b2c3
Create Date: 2026-09-07 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b9e0f1a2c3d4"
down_revision: str | None = "a8d9e0f1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_system", sa.String(length=80), nullable=True),
        sa.Column("batch_id", sa.String(length=120), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "owner_id",
        "api_key_id",
        "action",
        "entity_type",
        "entity_id",
        "source",
        "source_system",
        "batch_id",
        "reverted_at",
        "created_at",
    ):
        op.create_index(op.f("ix_agent_actions_" + column), "agent_actions", [column], unique=False)


def downgrade() -> None:
    op.drop_table("agent_actions")
