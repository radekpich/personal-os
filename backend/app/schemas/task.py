import enum
import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.task import RecurrenceMode, TaskPriority, TaskStatus
from app.schemas.tag import TagRead


def validate_rrule_value(value: str | None) -> str | None:
    if value is None:
        return None
    parts = dict(part.split("=", 1) for part in value.split(";") if "=" in part)
    if "FREQ" not in parts or parts["FREQ"] not in {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}:
        raise ValueError("recurrence_rule must be an RFC 5545 RRULE with supported FREQ")
    return value


class TaskView(str, enum.Enum):
    TODAY = "today"
    THIS_WEEK = "this_week"
    OVERDUE = "overdue"
    INBOX = "inbox"


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.INBOX
    priority: TaskPriority = TaskPriority.NONE
    due_date: date | None = None
    due_time: time | None = None
    estimate_minutes: int | None = Field(default=None, ge=1)
    category_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    recurrence_rule: str | None = Field(default=None, max_length=255)
    recurrence_mode: RecurrenceMode | None = None
    position: int = 0
    tag_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("recurrence_rule")
    @classmethod
    def validate_rrule(cls, value: str | None) -> str | None:
        return validate_rrule_value(value)

    @model_validator(mode="after")
    def recurrence_mode_matches_rule(self) -> "TaskBase":
        if (self.recurrence_rule is None) != (self.recurrence_mode is None):
            raise ValueError("recurrence_rule and recurrence_mode must be provided together")
        return self


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    due_time: time | None = None
    estimate_minutes: int | None = Field(default=None, ge=1)
    completed_at: datetime | None = None
    category_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    recurrence_rule: str | None = Field(default=None, max_length=255)
    recurrence_mode: RecurrenceMode | None = None
    position: int | None = None
    tag_ids: list[uuid.UUID] | None = None

    _validate_rrule = field_validator("recurrence_rule")(validate_rrule_value)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    due_time: time | None
    estimate_minutes: int | None
    completed_at: datetime | None
    category_id: uuid.UUID | None
    context_id: uuid.UUID | None
    vision_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    recurrence_template_id: uuid.UUID | None
    recurrence_rule: str | None
    recurrence_mode: RecurrenceMode | None
    position: int
    tags: list[TagRead]
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    page_size: int
