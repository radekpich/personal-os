"""add agent registry observability tables

Revision ID: c1d2e3f4a5b6
Revises: b9e0f1a2c3d4
Create Date: 2026-09-07 16:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b9e0f1a2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _idx(table: str, *columns: str) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def upgrade() -> None:
    op.create_table(
        "agent_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=True),
        sa.Column("host", sa.String(length=160), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("config_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name", "host", name="uq_agent_instance_identity"),
    )
    _idx("agent_instances", "owner_id", "name", "host", "last_heartbeat_at", "status", "config_hash")

    op.create_table(
        "agent_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schedule", sa.String(length=120), nullable=True),
        sa.Column("schedule_description", sa.String(length=240), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=30), nullable=True),
        sa.Column("last_duration_ms", sa.Integer(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("run_count", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("last_snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "name", name="uq_agent_job_name"),
    )
    _idx("agent_jobs", "agent_id", "name", "is_enabled", "next_run_at", "last_status")

    op.create_table(
        "agent_integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_snapshot_hash", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "name", "kind", name="uq_agent_integration_identity"),
    )
    _idx("agent_integrations", "agent_id", "name", "kind", "status")

    op.create_table(
        "agent_watches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("schedule", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer(), nullable=False),
        sa.Column("last_result", sa.Text(), nullable=True),
        sa.Column("last_snapshot_hash", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "name", name="uq_agent_watch_name"),
    )
    _idx("agent_watches", "agent_id", "name", "kind", "is_active")

    op.create_table(
        "agent_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("channel_type", sa.String(length=40), nullable=False),
        sa.Column("identifier", sa.String(length=240), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_count_24h", sa.Integer(), nullable=False),
        sa.Column("message_count_month", sa.Integer(), nullable=False),
        sa.Column("last_snapshot_hash", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "channel_type", "identifier", name="uq_agent_channel_identity"),
    )
    _idx("agent_channels", "agent_id", "channel_type", "is_active")

    op.create_table(
        "agent_capabilities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("last_snapshot_hash", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "name", name="uq_agent_capability_name"),
    )
    _idx("agent_capabilities", "agent_id", "name")

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("trigger", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost_estimate", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["agent_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _idx("agent_runs", "agent_id", "job_id", "trigger", "status", "started_at")

    op.create_table(
        "agent_config_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("change_type", sa.String(length=30), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_name", sa.String(length=240), nullable=False),
        sa.Column("diff_json", sa.JSON(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _idx("agent_config_changes", "agent_id", "timestamp", "change_type", "target_type", "target_name", "acknowledged_at")

    op.create_table(
        "agent_run_daily_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("run_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("total_duration_ms", sa.Integer(), nullable=False),
        sa.Column("total_tokens_used", sa.Integer(), nullable=False),
        sa.Column("total_cost_estimate", sa.Float(), nullable=False),
        sa.Column("summaries", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "day", name="uq_agent_run_daily_summary"),
    )
    _idx("agent_run_daily_summaries", "agent_id", "day")


def downgrade() -> None:
    for table in (
        "agent_run_daily_summaries",
        "agent_config_changes",
        "agent_runs",
        "agent_capabilities",
        "agent_channels",
        "agent_watches",
        "agent_integrations",
        "agent_jobs",
        "agent_instances",
    ):
        op.drop_table(table)
