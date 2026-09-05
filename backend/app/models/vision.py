import enum
import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VisionHorizon(str, enum.Enum):
    LIFE = "life"
    FIVE_YEARS = "5y"
    ONE_YEAR = "1y"
    QUARTER = "quarter"


class VisionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


class Vision(Base):
    __tablename__ = "visions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("visions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    horizon: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default=VisionHorizon.ONE_YEAR.value, index=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default=VisionStatus.ACTIVE.value, index=True
    )
    target_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
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
