"""add task recurrence fields

Revision ID: 7b1d2c5e9f40
Revises: 2f6d4e8c9a31
Create Date: 2026-09-04 20:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7b1d2c5e9f40"
down_revision: str | None = "2f6d4e8c9a31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("recurrence_template_id", sa.Uuid(), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_rule", sa.String(length=255), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_mode", sa.String(length=40), nullable=True))
    op.create_index(
        op.f("ix_tasks_recurrence_template_id"),
        "tasks",
        ["recurrence_template_id"],
        unique=False,
    )
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_recurrence_template_id_tasks",
            "tasks",
            ["recurrence_template_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("fk_tasks_recurrence_template_id_tasks", type_="foreignkey")
    op.drop_index(op.f("ix_tasks_recurrence_template_id"), table_name="tasks")
    op.drop_column("tasks", "recurrence_mode")
    op.drop_column("tasks", "recurrence_rule")
    op.drop_column("tasks", "recurrence_template_id")
