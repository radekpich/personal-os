"""add attachments

Revision ID: c8f2a1d9e0b4
Revises: a5c2f91e6b37
Create Date: 2026-09-05 14:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8f2a1d9e0b4"
down_revision: str | None = "a5c2f91e6b37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("thumbnail_path", sa.String(length=1024), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lon", sa.Float(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column(
            "processing_status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "checksum_sha256", name="uq_attachments_owner_checksum"),
    )
    op.create_index(
        op.f("ix_attachments_checksum_sha256"), "attachments", ["checksum_sha256"], unique=False
    )
    op.create_index(op.f("ix_attachments_mime_type"), "attachments", ["mime_type"], unique=False)
    op.create_index(op.f("ix_attachments_owner_id"), "attachments", ["owner_id"], unique=False)
    op.create_index(
        op.f("ix_attachments_processing_status"), "attachments", ["processing_status"], unique=False
    )

    op.create_table(
        "task_attachments",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "attachment_id"),
        sa.UniqueConstraint("task_id", "attachment_id", name="uq_task_attachments_pair"),
    )
    op.create_index(
        op.f("ix_task_attachments_attachment_id"),
        "task_attachments",
        ["attachment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_attachments_task_id"), "task_attachments", ["task_id"], unique=False
    )

    op.create_table(
        "note_attachments",
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("note_id", "attachment_id"),
        sa.UniqueConstraint("note_id", "attachment_id", name="uq_note_attachments_pair"),
    )
    op.create_index(
        op.f("ix_note_attachments_attachment_id"),
        "note_attachments",
        ["attachment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_attachments_note_id"), "note_attachments", ["note_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_note_attachments_note_id"), table_name="note_attachments")
    op.drop_index(op.f("ix_note_attachments_attachment_id"), table_name="note_attachments")
    op.drop_table("note_attachments")
    op.drop_index(op.f("ix_task_attachments_task_id"), table_name="task_attachments")
    op.drop_index(op.f("ix_task_attachments_attachment_id"), table_name="task_attachments")
    op.drop_table("task_attachments")
    op.drop_index(op.f("ix_attachments_processing_status"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_owner_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_mime_type"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_checksum_sha256"), table_name="attachments")
    op.drop_table("attachments")
