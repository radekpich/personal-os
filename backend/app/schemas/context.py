import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContextBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    position: int = 0
    is_archived: bool = False


class ContextCreate(ContextBase):
    pass


class ContextUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    position: int | None = None
    is_archived: bool | None = None


class ContextRead(ContextBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ContextList(BaseModel):
    items: list[ContextRead]
