import enum
import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus
from app.schemas.tag import TagRead


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
    parent_task_id: uuid.UUID | None = None
    position: int = 0
    tag_ids: list[uuid.UUID] = Field(default_factory=list)


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
    category_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    position: int | None = None
    tag_ids: list[uuid.UUID] | None = None


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
    parent_task_id: uuid.UUID | None
    position: int
    tags: list[TagRead]
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    page_size: int
