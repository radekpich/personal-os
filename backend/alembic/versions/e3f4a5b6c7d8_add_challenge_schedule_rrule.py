"""add challenge schedule rrule

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-09-10 11:25:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("challenges") as batch:
        batch.add_column(
            sa.Column("schedule_rrule", sa.String(length=500), nullable=False, server_default="FREQ=DAILY")
        )


def downgrade() -> None:
    with op.batch_alter_table("challenges") as batch:
        batch.drop_column("schedule_rrule")
