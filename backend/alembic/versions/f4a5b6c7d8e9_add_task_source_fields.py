"""add task source fields

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-09-10 12:20:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(
            sa.Column("source", sa.String(length=40), nullable=False, server_default="web")
        )
        batch.add_column(sa.Column("source_detail", sa.String(length=255), nullable=True))
        batch.create_index("ix_tasks_source", ["source"])

    op.execute("UPDATE tasks SET source = 'web' WHERE source IS NULL OR source = ''")


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_source")
        batch.drop_column("source_detail")
        batch.drop_column("source")
