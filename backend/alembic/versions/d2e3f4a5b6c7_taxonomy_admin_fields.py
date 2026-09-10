"""taxonomy admin fields

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-09-09 14:10:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("contexts") as batch:
        batch.add_column(sa.Column("color", sa.String(length=7), nullable=False, server_default="#64748B"))
        batch.add_column(sa.Column("icon", sa.String(length=80), nullable=False, server_default="map-pin"))
    with op.batch_alter_table("tags") as batch:
        batch.add_column(sa.Column("color", sa.String(length=7), nullable=False, server_default="#64748B"))
        batch.add_column(sa.Column("icon", sa.String(length=80), nullable=False, server_default="hash"))
        batch.add_column(sa.Column("position", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("tags") as batch:
        batch.drop_column("is_archived")
        batch.drop_column("position")
        batch.drop_column("icon")
        batch.drop_column("color")
    with op.batch_alter_table("contexts") as batch:
        batch.drop_column("icon")
        batch.drop_column("color")
