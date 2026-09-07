import enum
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentActionType(str, enum.Enum):
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    COMPLETE_TASK = "complete_task"
    ADD_NOTE = "add_note"
    UPDATE_NOTE = "update_note"
    CHECKIN = "checkin"
    ATTACH_FILE = "attach_file"
    SCHEDULE_TASK = "schedule_task"
    REVERT_ACTION = "revert_action"
    REVERT_BATCH = "revert_batch"


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, nullable=True, index=True)
    payload_json: Mapped[dict[str, Any] | list[Any] | str | None] = mapped_column(
        sa.JSON, nullable=True
    )
    before_json: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    result_json: Mapped[dict[str, Any] | list[Any] | str | None] = mapped_column(
        sa.JSON, nullable=True
    )
    reasoning: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source: Mapped[str] = mapped_column(sa.String(40), nullable=False, default="manual", index=True)
    source_system: Mapped[str | None] = mapped_column(sa.String(80), nullable=True, index=True)
    batch_id: Mapped[str | None] = mapped_column(sa.String(120), nullable=True, index=True)
    reverted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True
    )
