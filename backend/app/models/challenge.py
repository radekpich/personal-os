import enum
import uuid
from datetime import date as LocalDate
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChallengeType(str, enum.Enum):
    DAILY_ACTION = "daily_action"
    ABSTINENCE = "abstinence"


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    type: Mapped[str] = mapped_column(sa.String(30), nullable=False, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vision_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("visions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    target_days: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    allowed_gap_days: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True, index=True)
    color: Mapped[str] = mapped_column(sa.String(7), nullable=False, default="#22c55e")
    icon: Mapped[str] = mapped_column(sa.String(80), nullable=False, default="activity")
    current_streak: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
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


class CheckIn(Base):
    __tablename__ = "check_ins"
    __table_args__ = (
        sa.UniqueConstraint("challenge_id", "date", name="uq_check_ins_challenge_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[LocalDate] = mapped_column(sa.Date, nullable=False, index=True)
    value: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3), nullable=True)
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_relapse: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )


class ChallengePause(Base):
    __tablename__ = "challenge_pauses"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[LocalDate] = mapped_column(sa.Date, nullable=False)
    end_date: Mapped[LocalDate | None] = mapped_column(sa.Date, nullable=True)
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )
