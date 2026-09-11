"""add task completed_by

Revision ID: g5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-09-11 06:15:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g5b6c7d8e9f0"
down_revision: str | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("completed_by", sa.String(length=20), nullable=True))

    op.execute("UPDATE tasks SET completed_by = updated_by WHERE completed_at IS NOT NULL AND completed_by IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("completed_by")
