import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    api_key_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    payload_json: dict[str, Any] | list[Any] | str | None
    before_json: dict[str, Any] | None
    result_json: dict[str, Any] | list[Any] | str | None
    reasoning: str
    source: str
    source_system: str | None
    batch_id: str | None
    reverted_at: datetime | None
    latency_ms: int | None
    created_at: datetime


class AgentActionList(BaseModel):
    items: list[AgentActionRead]
    total: int
    page: int
    page_size: int


class RevertBatchRequest(BaseModel):
    batch_id: str | None = Field(default=None, min_length=1)
    created_from: datetime | None = None
    created_to: datetime | None = None


class RevertResult(BaseModel):
    reverted_action_ids: list[uuid.UUID]
