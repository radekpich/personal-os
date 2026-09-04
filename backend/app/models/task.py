import enum
import uuid
from datetime import date, datetime, time

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tag import Tag


class TaskStatus(str, enum.Enum):
    INBOX = "inbox"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecurrenceMode(str, enum.Enum):
    FIXED = "fixed"
    AFTER_COMPLETION = "after_completion"


task_tags = sa.Table(
    "task_tags",
    Base.metadata,
    sa.Column(
        "task_id",
        sa.Uuid(),
        sa.ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "tag_id",
        sa.Uuid(),
        sa.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(40), nullable=False, default=TaskStatus.INBOX.value, index=True
    )
    priority: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default=TaskPriority.NONE.value, index=True
    )
    due_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True, index=True)
    due_time: Mapped[time | None] = mapped_column(sa.Time, nullable=True)
    estimate_minutes: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    context_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("contexts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recurrence_template_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recurrence_rule: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    recurrence_mode: Mapped[str | None] = mapped_column(sa.String(40), nullable=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    tags: Mapped[list[Tag]] = relationship(
        secondary=task_tags, lazy="selectin", order_by="Tag.name"
    )
