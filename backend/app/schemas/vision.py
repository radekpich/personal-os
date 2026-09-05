import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.vision import VisionHorizon, VisionStatus


class VisionBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    horizon: VisionHorizon = VisionHorizon.ONE_YEAR
    status: VisionStatus = VisionStatus.ACTIVE
    target_date: date | None = None
    category_id: uuid.UUID | None = None
    position: int = 0


class VisionCreate(VisionBase):
    pass


class VisionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    horizon: VisionHorizon | None = None
    status: VisionStatus | None = None
    target_date: date | None = None
    category_id: uuid.UUID | None = None
    position: int | None = None


class VisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    parent_id: uuid.UUID | None
    horizon: VisionHorizon
    status: VisionStatus
    target_date: date | None
    category_id: uuid.UUID | None
    position: int
    created_at: datetime
    updated_at: datetime


class VisionList(BaseModel):
    items: list[VisionRead]


class VisionTreeNode(VisionRead):
    children: list["VisionTreeNode"] = Field(default_factory=list)


class VisionProgress(BaseModel):
    vision_id: uuid.UUID
    total_tasks: int
    done_tasks: int
    last_activity_at: datetime | None
    stagnation_days: int | None


class StagnatingVision(BaseModel):
    vision: VisionRead
    progress: VisionProgress


class StagnatingVisionList(BaseModel):
    items: list[StagnatingVision]


class VisionTree(BaseModel):
    items: list[VisionTreeNode]
