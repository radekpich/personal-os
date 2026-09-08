import uuid
from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentInstance(Base):
    __tablename__ = "agent_instances"
    __table_args__ = (
        sa.UniqueConstraint("owner_id", "name", "host", name="uq_agent_instance_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(80), nullable=False, index=True)
    version: Mapped[str | None] = mapped_column(sa.String(80), nullable=True)
    host: Mapped[str] = mapped_column(sa.String(160), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="unknown", index=True
    )
    last_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    config_hash: Mapped[str | None] = mapped_column(sa.String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    jobs: Mapped[list["AgentJob"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    integrations: Mapped[list["AgentIntegration"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    watches: Mapped[list["AgentWatch"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    channels: Mapped[list["AgentChannel"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    capabilities: Mapped[list["AgentCapability"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )
    runs: Mapped[list["AgentRun"]] = relationship(back_populates="agent", lazy="selectin")
    config_changes: Mapped[list["AgentConfigChange"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )


class AgentJob(Base):
    __tablename__ = "agent_jobs"
    __table_args__ = (sa.UniqueConstraint("agent_id", "name", name="uq_agent_job_name"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    schedule: Mapped[str | None] = mapped_column(sa.String(120), nullable=True)
    schedule_description: Mapped[str | None] = mapped_column(sa.String(240), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    last_status: Mapped[str | None] = mapped_column(sa.String(30), nullable=True, index=True)
    last_duration_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    run_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    tags: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    last_snapshot_hash: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    agent: Mapped[AgentInstance] = relationship(back_populates="jobs")
    runs: Mapped[list["AgentRun"]] = relationship(back_populates="job", lazy="selectin")


class AgentIntegration(Base):
    __tablename__ = "agent_integrations"
    __table_args__ = (
        sa.UniqueConstraint("agent_id", "name", "kind", name="uq_agent_integration_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    scopes: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="active", index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    error_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_snapshot_hash: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    agent: Mapped[AgentInstance] = relationship(back_populates="integrations")


class AgentWatch(Base):
    __tablename__ = "agent_watches"
    __table_args__ = (sa.UniqueConstraint("agent_id", "name", name="uq_agent_watch_name"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    kind: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON, nullable=False, default=dict)
    schedule: Mapped[str | None] = mapped_column(sa.String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True, index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    trigger_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    last_result: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_snapshot_hash: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    agent: Mapped[AgentInstance] = relationship(back_populates="watches")


class AgentChannel(Base):
    __tablename__ = "agent_channels"
    __table_args__ = (
        sa.UniqueConstraint(
            "agent_id", "channel_type", "identifier", name="uq_agent_channel_identity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(sa.String(240), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True, index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    message_count_24h: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    message_count_month: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    last_snapshot_hash: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    agent: Mapped[AgentInstance] = relationship(back_populates="channels")


class AgentCapability(Base):
    __tablename__ = "agent_capabilities"
    __table_args__ = (sa.UniqueConstraint("agent_id", "name", name="uq_agent_capability_name"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON, nullable=False, default=dict)
    last_snapshot_hash: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    agent: Mapped[AgentInstance] = relationship(back_populates="capabilities")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    trigger: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(30), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cost_estimate: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    agent: Mapped[AgentInstance] = relationship(back_populates="runs")
    job: Mapped[AgentJob | None] = relationship(back_populates="runs")


class AgentConfigChange(Base):
    __tablename__ = "agent_config_changes"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True
    )
    change_type: Mapped[str] = mapped_column(sa.String(30), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    target_name: Mapped[str] = mapped_column(sa.String(240), nullable=False, index=True)
    diff_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON, nullable=False, default=dict)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )

    agent: Mapped[AgentInstance] = relationship(back_populates="config_changes")


class AgentRunDailySummary(Base):
    __tablename__ = "agent_run_daily_summaries"
    __table_args__ = (sa.UniqueConstraint("agent_id", "day", name="uq_agent_run_daily_summary"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("agent_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[date] = mapped_column(sa.Date, nullable=False, index=True)
    run_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    total_duration_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    total_tokens_used: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    summaries: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
