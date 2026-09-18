"""add external calendars and calendar request queue

Revision ID: h6c7d8e9f0a1
Revises: g5b6c7d8e9f0
Create Date: 2026-09-16 07:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h6c7d8e9f0a1"
down_revision: str | None = "g5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_calendars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("can_write", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "external_id", name="uq_external_calendars_owner_external"),
    )
    op.create_index(op.f("ix_external_calendars_owner_id"), "external_calendars", ["owner_id"], unique=False)
    op.create_index(op.f("ix_external_calendars_last_synced_at"), "external_calendars", ["last_synced_at"], unique=False)

    op.create_table(
        "calendar_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("calendar_external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("all_day", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reminder_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_event_id", sa.String(length=255), nullable=True),
        sa.Column("external_event_link", sa.String(length=1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["claimed_by"], ["api_keys.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "idempotency_key", name="uq_calendar_requests_owner_idempotency"),
    )
    op.create_index(op.f("ix_calendar_requests_owner_id"), "calendar_requests", ["owner_id"], unique=False)
    op.create_index(op.f("ix_calendar_requests_task_id"), "calendar_requests", ["task_id"], unique=False)
    op.create_index(op.f("ix_calendar_requests_operation"), "calendar_requests", ["operation"], unique=False)
    op.create_index(op.f("ix_calendar_requests_calendar_external_id"), "calendar_requests", ["calendar_external_id"], unique=False)
    op.create_index(op.f("ix_calendar_requests_status"), "calendar_requests", ["status"], unique=False)
    op.create_index(op.f("ix_calendar_requests_created_at"), "calendar_requests", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_calendar_requests_created_at"), table_name="calendar_requests")
    op.drop_index(op.f("ix_calendar_requests_status"), table_name="calendar_requests")
    op.drop_index(op.f("ix_calendar_requests_calendar_external_id"), table_name="calendar_requests")
    op.drop_index(op.f("ix_calendar_requests_operation"), table_name="calendar_requests")
    op.drop_index(op.f("ix_calendar_requests_task_id"), table_name="calendar_requests")
    op.drop_index(op.f("ix_calendar_requests_owner_id"), table_name="calendar_requests")
    op.drop_table("calendar_requests")
    op.drop_index(op.f("ix_external_calendars_last_synced_at"), table_name="external_calendars")
    op.drop_index(op.f("ix_external_calendars_owner_id"), table_name="external_calendars")
    op.drop_table("external_calendars")
