"""add visions and task vision link

Revision ID: d4b8f72c9e11
Revises: 91c0a6e7d2b8
Create Date: 2026-09-05 07:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4b8f72c9e11"
down_revision: str | None = "91c0a6e7d2b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "visions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("horizon", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["visions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_visions_category_id"), "visions", ["category_id"], unique=False)
    op.create_index(op.f("ix_visions_horizon"), "visions", ["horizon"], unique=False)
    op.create_index(op.f("ix_visions_owner_id"), "visions", ["owner_id"], unique=False)
    op.create_index(op.f("ix_visions_parent_id"), "visions", ["parent_id"], unique=False)
    op.create_index(op.f("ix_visions_status"), "visions", ["status"], unique=False)
    op.create_index(op.f("ix_visions_target_date"), "visions", ["target_date"], unique=False)
    op.add_column("tasks", sa.Column("vision_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_tasks_vision_id"), "tasks", ["vision_id"], unique=False)
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_vision_id_visions",
            "visions",
            ["vision_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("fk_tasks_vision_id_visions", type_="foreignkey")
    op.drop_index(op.f("ix_tasks_vision_id"), table_name="tasks")
    op.drop_column("tasks", "vision_id")
    op.drop_index(op.f("ix_visions_target_date"), table_name="visions")
    op.drop_index(op.f("ix_visions_status"), table_name="visions")
    op.drop_index(op.f("ix_visions_parent_id"), table_name="visions")
    op.drop_index(op.f("ix_visions_owner_id"), table_name="visions")
    op.drop_index(op.f("ix_visions_horizon"), table_name="visions")
    op.drop_index(op.f("ix_visions_category_id"), table_name="visions")
    op.drop_table("visions")
