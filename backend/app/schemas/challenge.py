import uuid
from datetime import date as LocalDate
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.challenge import ChallengeType


class ChallengeBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: ChallengeType = ChallengeType.DAILY_ACTION
    category_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    started_at: datetime | None = None
    target_days: int | None = Field(default=None, ge=1)
    allowed_gap_days: int = Field(default=0, ge=0, le=30)
    is_active: bool = True
    color: str = Field(default="#22c55e", min_length=7, max_length=7)
    icon: str = Field(default="activity", min_length=1, max_length=80)

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be hex format #RRGGBB")
        if any(char not in "0123456789abcdefABCDEF" for char in value[1:]):
            raise ValueError("color must be hex format #RRGGBB")
        return value


class ChallengeCreate(ChallengeBase):
    pass


class ChallengeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    started_at: datetime | None = None
    target_days: int | None = Field(default=None, ge=1)
    allowed_gap_days: int | None = Field(default=None, ge=0, le=30)
    is_active: bool | None = None
    color: str | None = Field(default=None, min_length=7, max_length=7)
    icon: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("color")
    @classmethod
    def validate_optional_hex_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return ChallengeBase.validate_hex_color(value)


class ChallengeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    type: ChallengeType
    category_id: uuid.UUID | None
    vision_id: uuid.UUID | None
    started_at: datetime
    target_days: int | None
    allowed_gap_days: int
    is_active: bool
    color: str
    icon: str
    current_streak: int
    longest_streak: int
    created_at: datetime
    updated_at: datetime


class ChallengeList(BaseModel):
    items: list[ChallengeRead]


class CheckInCreate(BaseModel):
    date: LocalDate | None = None
    value: float | None = None
    note: str | None = None
    is_relapse: bool = False


class CheckInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    challenge_id: uuid.UUID
    date: LocalDate
    value: float | None
    note: str | None
    is_relapse: bool
    created_at: datetime
    updated_at: datetime


class CheckInResult(BaseModel):
    check_in: CheckInRead
    current_streak: int
    longest_streak: int


class ChallengePauseCreate(BaseModel):
    start_date: LocalDate
    end_date: LocalDate | None = None
    note: str | None = None


class ChallengePauseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    challenge_id: uuid.UUID
    start_date: LocalDate
    end_date: LocalDate | None
    note: str | None
    created_at: datetime
    updated_at: datetime
