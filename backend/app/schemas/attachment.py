from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    storage_path: str
    thumbnail_path: str | None
    original_filename: str
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    checksum_sha256: str
    captured_at: datetime | None
    gps_lat: float | None
    gps_lon: float | None
    caption: str | None
    processing_status: str
    created_at: datetime
    deleted_at: datetime | None


class AttachmentUpdate(BaseModel):
    caption: str | None = None


class AttachmentList(BaseModel):
    items: list[AttachmentRead]


class TaskAttachmentCreate(BaseModel):
    attachment_id: UUID
    position: int = 0


class TaskAttachmentRead(BaseModel):
    task_id: UUID
    attachment_id: UUID
    position: int


class NoteAttachmentCreate(BaseModel):
    attachment_id: UUID
    position: int = 0


class NoteAttachmentRead(BaseModel):
    note_id: UUID
    attachment_id: UUID
    position: int


class StorageUsage(BaseModel):
    file_count: int
    used_bytes: int
    max_bytes: int
    remaining_bytes: int
    used_percent: float
