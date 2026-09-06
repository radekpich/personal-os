import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttachmentProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        sa.UniqueConstraint("owner_id", "checksum_sha256", name="uq_attachments_owner_checksum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    original_filename: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(sa.String(120), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    captured_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    gps_lat: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    gps_lon: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    caption: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default=AttachmentProcessingStatus.PENDING.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)


class TaskAttachment(Base):
    __tablename__ = "task_attachments"
    __table_args__ = (
        sa.UniqueConstraint("task_id", "attachment_id", name="uq_task_attachments_pair"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("attachments.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)


class NoteAttachment(Base):
    __tablename__ = "note_attachments"
    __table_args__ = (
        sa.UniqueConstraint("note_id", "attachment_id", name="uq_note_attachments_pair"),
    )

    note_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True
    )
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("attachments.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
