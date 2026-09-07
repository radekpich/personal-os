import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.models.note import NoteKind


class NoteBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str | None = None
    kind: NoteKind = NoteKind.NOTE
    entry_date: date | None = None
    entry_time: time | None = None
    mood: str | None = Field(default=None, max_length=40)
    category_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = None
    kind: NoteKind | None = None
    entry_date: date | None = None
    entry_time: time | None = None
    mood: str | None = Field(default=None, max_length=40)
    category_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    body: str | None
    kind: NoteKind
    entry_date: date | None
    entry_time: time | None
    mood: str | None
    category_id: uuid.UUID | None
    vision_id: uuid.UUID | None
    task_id: uuid.UUID | None
    version: int
    created_by: str
    updated_by: str
    api_key_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class NoteList(BaseModel):
    items: list[NoteRead]
    total: int
    page: int
    page_size: int
