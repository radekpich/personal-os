"""add notes

Revision ID: e2a7b4c9d1f3
Revises: c8f2a1d9e0b4
Create Date: 2026-09-06 18:26:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2a7b4c9d1f3"
down_revision: str | None = "c8f2a1d9e0b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="note"),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("entry_time", sa.Time(), nullable=True),
        sa.Column("mood", sa.String(length=40), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("vision_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vision_id"], ["visions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notes_category_id"), "notes", ["category_id"], unique=False)
    op.create_index(op.f("ix_notes_deleted_at"), "notes", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_notes_entry_date"), "notes", ["entry_date"], unique=False)
    op.create_index(op.f("ix_notes_kind"), "notes", ["kind"], unique=False)
    op.create_index(op.f("ix_notes_owner_id"), "notes", ["owner_id"], unique=False)
    op.create_index(op.f("ix_notes_task_id"), "notes", ["task_id"], unique=False)
    op.create_index(op.f("ix_notes_vision_id"), "notes", ["vision_id"], unique=False)

    with op.batch_alter_table("note_attachments", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_note_attachments_note_id_notes", "notes", ["note_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    with op.batch_alter_table("note_attachments", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_note_attachments_note_id_notes", type_="foreignkey")

    op.drop_index(op.f("ix_notes_vision_id"), table_name="notes")
    op.drop_index(op.f("ix_notes_task_id"), table_name="notes")
    op.drop_index(op.f("ix_notes_owner_id"), table_name="notes")
    op.drop_index(op.f("ix_notes_kind"), table_name="notes")
    op.drop_index(op.f("ix_notes_entry_date"), table_name="notes")
    op.drop_index(op.f("ix_notes_deleted_at"), table_name="notes")
    op.drop_index(op.f("ix_notes_category_id"), table_name="notes")
    op.drop_table("notes")
