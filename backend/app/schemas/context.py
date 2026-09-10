import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.category import validate_hex_color


class ContextBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    color: str = Field(default="#64748B", min_length=7, max_length=7)
    icon: str = Field(default="map-pin", min_length=1, max_length=80)
    position: int = 0
    is_archived: bool = False

    _validate_color = field_validator("color")(validate_hex_color)


class ContextCreate(ContextBase):
    pass


class ContextUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, min_length=7, max_length=7)
    icon: str | None = Field(default=None, min_length=1, max_length=80)
    position: int | None = None
    is_archived: bool | None = None

    @field_validator("color")
    @classmethod
    def validate_optional_hex_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_hex_color(value)


class ContextRead(ContextBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    task_count: int = 0
    created_at: datetime
    updated_at: datetime


class ContextList(BaseModel):
    items: list[ContextRead]
