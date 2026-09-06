import enum
import uuid
from datetime import date, datetime, time

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NoteKind(str, enum.Enum):
    NOTE = "note"
    DIARY = "diary"
    MEETING = "meeting"
    IDEA = "idea"


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    kind: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default=NoteKind.NOTE.value, index=True
    )
    entry_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True, index=True)
    entry_time: Mapped[time | None] = mapped_column(sa.Time, nullable=True)
    mood: Mapped[str | None] = mapped_column(sa.String(40), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vision_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("visions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
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
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
