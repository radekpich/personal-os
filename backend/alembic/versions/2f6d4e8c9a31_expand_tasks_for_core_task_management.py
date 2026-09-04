"""expand tasks for core task management

Revision ID: 2f6d4e8c9a31
Revises: b7c84319d5aa
Create Date: 2026-09-04 20:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2f6d4e8c9a31"
down_revision: str | None = "b7c84319d5aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="none"),
    )
    op.add_column("tasks", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("tasks", sa.Column("due_time", sa.Time(), nullable=True))
    op.add_column("tasks", sa.Column("estimate_minutes", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("category_id", sa.Uuid(), nullable=True))
    op.add_column("tasks", sa.Column("context_id", sa.Uuid(), nullable=True))
    op.add_column("tasks", sa.Column("parent_task_id", sa.Uuid(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_index(op.f("ix_tasks_priority"), "tasks", ["priority"], unique=False)
    op.create_index(op.f("ix_tasks_due_date"), "tasks", ["due_date"], unique=False)
    op.create_index(op.f("ix_tasks_category_id"), "tasks", ["category_id"], unique=False)
    op.create_index(op.f("ix_tasks_context_id"), "tasks", ["context_id"], unique=False)
    op.create_index(op.f("ix_tasks_parent_task_id"), "tasks", ["parent_task_id"], unique=False)

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_category_id_categories",
            "categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_tasks_context_id_contexts", "contexts", ["context_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            "fk_tasks_parent_task_id_tasks",
            "tasks",
            ["parent_task_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("fk_tasks_parent_task_id_tasks", type_="foreignkey")
        batch_op.drop_constraint("fk_tasks_context_id_contexts", type_="foreignkey")
        batch_op.drop_constraint("fk_tasks_category_id_categories", type_="foreignkey")

    op.drop_index(op.f("ix_tasks_parent_task_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_context_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_category_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_due_date"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_priority"), table_name="tasks")

    op.drop_column("tasks", "position")
    op.drop_column("tasks", "parent_task_id")
    op.drop_column("tasks", "context_id")
    op.drop_column("tasks", "category_id")
    op.drop_column("tasks", "completed_at")
    op.drop_column("tasks", "estimate_minutes")
    op.drop_column("tasks", "due_time")
    op.drop_column("tasks", "due_date")
    op.drop_column("tasks", "priority")
    op.drop_column("tasks", "description")
