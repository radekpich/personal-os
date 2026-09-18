import enum
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CalendarRequestOperation(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class CalendarRequestStatus(str, enum.Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExternalCalendar(Base):
    __tablename__ = "external_calendars"
    __table_args__ = (
        sa.UniqueConstraint("owner_id", "external_id", name="uq_external_calendars_owner_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    color: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    can_write: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    is_shared: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    is_primary: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    is_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.true()
    )
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class CalendarRequest(Base):
    __tablename__ = "calendar_requests"
    __table_args__ = (
        sa.UniqueConstraint(
            "owner_id", "idempotency_key", name="uq_calendar_requests_owner_idempotency"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation: Mapped[str] = mapped_column(sa.String(20), nullable=False, index=True)
    calendar_external_id: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    all_day: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    reminder_minutes: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default=CalendarRequestStatus.PENDING.value,
        server_default=CalendarRequestStatus.PENDING.value,
        index=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    claimed_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    external_event_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    external_event_link: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0, server_default="0"
    )
    idempotency_key: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
