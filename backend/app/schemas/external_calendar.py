import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.external_calendar import CalendarRequestOperation, CalendarRequestStatus


class ExternalCalendarSyncItem(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    color: str | None = Field(default=None, max_length=32)
    can_write: bool = False
    is_shared: bool = False
    is_primary: bool = False
    is_enabled: bool = True
    is_default: bool = False


class ExternalCalendarSyncRequest(BaseModel):
    calendars: list[ExternalCalendarSyncItem]


class ExternalCalendarUpdate(BaseModel):
    is_enabled: bool | None = None
    is_default: bool | None = None


class ExternalCalendarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    external_id: str
    name: str
    color: str | None
    can_write: bool
    is_shared: bool
    is_primary: bool
    is_enabled: bool
    is_default: bool
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime


class ExternalCalendarList(BaseModel):
    items: list[ExternalCalendarRead]


class CalendarRequestCreate(BaseModel):
    operation: CalendarRequestOperation = CalendarRequestOperation.CREATE
    calendar_external_id: str = Field(min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    reminder_minutes: int | None = Field(default=None, ge=0, le=10080)
    idempotency_key: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def ends_after_start(self) -> "CalendarRequestCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class CalendarRequestComplete(BaseModel):
    external_event_id: str | None = Field(default=None, max_length=255)
    external_event_link: str | None = Field(default=None, max_length=1024)
    error_message: str | None = None


class CalendarRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    task_id: uuid.UUID
    operation: CalendarRequestOperation
    calendar_external_id: str
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    all_day: bool
    reminder_minutes: int | None
    status: CalendarRequestStatus
    claimed_at: datetime | None
    claimed_by: uuid.UUID | None
    completed_at: datetime | None
    external_event_id: str | None
    external_event_link: str | None
    error_message: str | None
    attempt_count: int
    idempotency_key: str
    created_at: datetime
    calendar_name: str | None = None
    calendar_color: str | None = None


class CalendarRequestList(BaseModel):
    items: list[CalendarRequestRead]
