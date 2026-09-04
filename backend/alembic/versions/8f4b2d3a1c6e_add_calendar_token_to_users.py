"""add calendar token to users

Revision ID: 8f4b2d3a1c6e
Revises: 4e41d697105a
Create Date: 2026-09-04 17:30:00.000000

"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8f4b2d3a1c6e"
down_revision: str | None = "4e41d697105a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("calendar_token", sa.String(length=64), nullable=True))

    connection = op.get_bind()
    user_rows = connection.execute(sa.text("SELECT id FROM users")).fetchall()
    for row in user_rows:
        connection.execute(
            sa.text("UPDATE users SET calendar_token = :token WHERE id = :user_id"),
            {"token": secrets.token_urlsafe(32), "user_id": row.id},
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "calendar_token",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_index("ix_users_calendar_token", ["calendar_token"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_calendar_token")
        batch_op.drop_column("calendar_token")
