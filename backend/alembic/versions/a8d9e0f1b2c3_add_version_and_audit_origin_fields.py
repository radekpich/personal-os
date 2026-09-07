"""add version and audit origin fields

Revision ID: a8d9e0f1b2c3
Revises: f7a1c2d3e4b5
Create Date: 2026-09-07 08:06:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a8d9e0f1b2c3"
down_revision: str | None = "f7a1c2d3e4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_fields(table: str) -> None:
    with op.batch_alter_table(table, recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column(
                "created_by", sa.String(length=20), nullable=False, server_default="user"
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_by", sa.String(length=20), nullable=False, server_default="user"
            )
        )
        batch_op.add_column(sa.Column("api_key_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table}_api_key_id_api_keys",
            "api_keys",
            ["api_key_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(batch_op.f(f"ix_{table}_api_key_id"), ["api_key_id"])


def _drop_fields(table: str) -> None:
    with op.batch_alter_table(table, recreate="always") as batch_op:
        batch_op.drop_index(batch_op.f(f"ix_{table}_api_key_id"))
        batch_op.drop_constraint(f"fk_{table}_api_key_id_api_keys", type_="foreignkey")
        batch_op.drop_column("api_key_id")
        batch_op.drop_column("updated_by")
        batch_op.drop_column("created_by")
        batch_op.drop_column("version")


def upgrade() -> None:
    _add_fields("tasks")
    _add_fields("notes")


def downgrade() -> None:
    _drop_fields("notes")
    _drop_fields("tasks")
