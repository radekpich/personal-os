import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    color: str = Field(min_length=7, max_length=7)
    icon: str = Field(min_length=1, max_length=80)
    parent_id: uuid.UUID | None = None
    position: int = 0
    is_archived: bool = False

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be hex format #RRGGBB")
        hex_part = value[1:]
        if any(char not in "0123456789abcdefABCDEF" for char in hex_part):
            raise ValueError("color must be hex format #RRGGBB")
        return value


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, min_length=7, max_length=7)
    icon: str | None = Field(default=None, min_length=1, max_length=80)
    parent_id: uuid.UUID | None = None
    position: int | None = None
    is_archived: bool | None = None

    @field_validator("color")
    @classmethod
    def validate_optional_hex_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return CategoryBase.validate_hex_color(value)


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CategoryList(BaseModel):
    items: list[CategoryRead]
