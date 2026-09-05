import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.challenge import Challenge, ChallengePause, ChallengeType, CheckIn
from app.models.user import User
from app.schemas.challenge import ChallengeCreate, ChallengeUpdate, CheckInCreate
from app.services import category_service, vision_service

BACKFILL_LIMIT_DAYS = 7


def _user_zone(owner: User) -> ZoneInfo:
    try:
        return ZoneInfo(owner.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user timezone is invalid",
        ) from exc


def _today_for_user(owner: User) -> date:
    return datetime.now(_user_zone(owner)).date()


def _normalize_started_at(owner: User, started_at: datetime | None) -> datetime:
    if started_at is None:
        return datetime.now(_user_zone(owner))
    if started_at.tzinfo is None:
        return started_at.replace(tzinfo=_user_zone(owner))
    return started_at


def _decimal_value(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


async def list_challenges(db: AsyncSession, owner: User) -> list[Challenge]:
    result = await db.execute(
        select(Challenge)
        .where(Challenge.owner_id == owner.id, Challenge.deleted_at.is_(None))
        .order_by(Challenge.is_active.desc(), Challenge.created_at.desc())
    )
    return list(result.scalars().all())


async def get_challenge(db: AsyncSession, owner: User, challenge_id: uuid.UUID) -> Challenge:
    result = await db.execute(
        select(Challenge).where(
            Challenge.id == challenge_id,
            Challenge.owner_id == owner.id,
            Challenge.deleted_at.is_(None),
        )
    )
    challenge = result.scalar_one_or_none()
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="challenge not found")
    return challenge


async def _validate_links(
    db: AsyncSession,
    owner: User,
    category_id: uuid.UUID | None,
    vision_id: uuid.UUID | None,
) -> None:
    if category_id is not None:
        await category_service.get_category(db, owner, category_id)
    if vision_id is not None:
        await vision_service.get_vision(db, owner, vision_id)


async def create_challenge(db: AsyncSession, owner: User, payload: ChallengeCreate) -> Challenge:
    await _validate_links(db, owner, payload.category_id, payload.vision_id)
    challenge = Challenge(
        owner_id=owner.id,
        title=payload.title,
        description=payload.description,
        type=payload.type.value,
        category_id=payload.category_id,
        vision_id=payload.vision_id,
        started_at=_normalize_started_at(owner, payload.started_at),
        target_days=payload.target_days,
        allowed_gap_days=payload.allowed_gap_days,
        is_active=payload.is_active,
        color=payload.color,
        icon=payload.icon,
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge


async def update_challenge(
    db: AsyncSession, owner: User, challenge_id: uuid.UUID, payload: ChallengeUpdate
) -> Challenge:
    challenge = await get_challenge(db, owner, challenge_id)
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes or "vision_id" in changes:
        await _validate_links(
            db,
            owner,
            payload.category_id if "category_id" in changes else challenge.category_id,
            payload.vision_id if "vision_id" in changes else challenge.vision_id,
        )
    for field in (
        "title",
        "description",
        "category_id",
        "vision_id",
        "target_days",
        "allowed_gap_days",
        "is_active",
        "color",
        "icon",
    ):
        if field in changes:
            setattr(challenge, field, changes[field])
    if "started_at" in changes:
        challenge.started_at = _normalize_started_at(owner, payload.started_at)
    await _recalculate_streaks(db, owner, challenge)
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge


async def delete_challenge(db: AsyncSession, owner: User, challenge_id: uuid.UUID) -> None:
    challenge = await get_challenge(db, owner, challenge_id)
    challenge.deleted_at = datetime.now(UTC)
    db.add(challenge)
    await db.commit()


async def check_in_challenge(
    db: AsyncSession, owner: User, challenge_id: uuid.UUID, payload: CheckInCreate
) -> tuple[CheckIn, bool, Challenge]:
    challenge = await get_challenge(db, owner, challenge_id)
    local_today = _today_for_user(owner)
    check_date = payload.date or local_today
    if check_date > local_today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="check-in date cannot be in future"
        )
    if check_date < local_today - timedelta(days=BACKFILL_LIMIT_DAYS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="check-in date is too far in the past"
        )
    if challenge.type == ChallengeType.ABSTINENCE.value and not payload.is_relapse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="abstinence challenges accept relapse check-ins only",
        )

    existing_result = await db.execute(
        select(CheckIn).where(CheckIn.challenge_id == challenge.id, CheckIn.date == check_date)
    )
    check_in = existing_result.scalar_one_or_none()
    created = check_in is None
    if check_in is None:
        check_in = CheckIn(
            owner_id=owner.id,
            challenge_id=challenge.id,
            date=check_date,
            value=_decimal_value(payload.value),
            note=payload.note,
            is_relapse=payload.is_relapse,
        )
    else:
        check_in.value = _decimal_value(payload.value)
        check_in.note = payload.note
        check_in.is_relapse = payload.is_relapse
    db.add(check_in)
    await db.flush()
    await _recalculate_streaks(db, owner, challenge)
    db.add(challenge)
    await db.commit()
    await db.refresh(check_in)
    await db.refresh(challenge)
    return check_in, created, challenge


async def create_pause(
    db: AsyncSession,
    owner: User,
    challenge_id: uuid.UUID,
    start_date: date,
    end_date: date | None,
    note: str | None,
) -> ChallengePause:
    challenge = await get_challenge(db, owner, challenge_id)
    pause = ChallengePause(
        owner_id=owner.id,
        challenge_id=challenge.id,
        start_date=start_date,
        end_date=end_date,
        note=note,
    )
    db.add(pause)
    await db.flush()
    await _recalculate_streaks(db, owner, challenge)
    db.add(challenge)
    await db.commit()
    await db.refresh(pause)
    return pause


async def _recalculate_streaks(db: AsyncSession, owner: User, challenge: Challenge) -> None:
    if challenge.type == ChallengeType.ABSTINENCE.value:
        current, longest = await _calculate_abstinence_streaks(db, owner, challenge)
    else:
        current, longest = await _calculate_daily_action_streaks(db, owner, challenge)
    challenge.current_streak = current
    challenge.longest_streak = longest


async def _challenge_pauses(
    db: AsyncSession, owner: User, challenge: Challenge
) -> list[ChallengePause]:
    result = await db.execute(
        select(ChallengePause)
        .where(ChallengePause.challenge_id == challenge.id, ChallengePause.owner_id == owner.id)
        .order_by(ChallengePause.start_date)
    )
    return list(result.scalars().all())


def _is_paused(day: date, pauses: list[ChallengePause]) -> bool:
    return any(pause.start_date <= day <= (pause.end_date or day) for pause in pauses)


def _active_gap_days(
    start_exclusive: date, end_exclusive: date, pauses: list[ChallengePause]
) -> int:
    gap = 0
    cursor = start_exclusive + timedelta(days=1)
    while cursor < end_exclusive:
        if not _is_paused(cursor, pauses):
            gap += 1
        cursor += timedelta(days=1)
    return gap


async def _calculate_daily_action_streaks(
    db: AsyncSession, owner: User, challenge: Challenge
) -> tuple[int, int]:
    result = await db.execute(
        select(CheckIn.date)
        .where(
            CheckIn.challenge_id == challenge.id,
            CheckIn.owner_id == owner.id,
            CheckIn.is_relapse.is_(False),
        )
        .order_by(CheckIn.date)
    )
    days = [day for day in result.scalars().all()]
    if not days:
        return 0, 0
    pauses = await _challenge_pauses(db, owner, challenge)
    longest = 1
    run = 1
    previous = days[0]
    for current in days[1:]:
        gap = _active_gap_days(previous, current, pauses)
        if gap <= challenge.allowed_gap_days:
            run += gap + 1
        else:
            longest = max(longest, run)
            run = 1
        previous = current
    longest = max(longest, run)
    today = _today_for_user(owner)
    trailing_gap = _active_gap_days(days[-1], today + timedelta(days=1), pauses)
    if days[-1] != today:
        trailing_gap = max(trailing_gap - 1, 0)
    current_streak = run if trailing_gap <= challenge.allowed_gap_days else 0
    return current_streak, longest


def _active_elapsed_days(
    start_exclusive: date, end_inclusive: date, pauses: list[ChallengePause]
) -> int:
    days = 0
    cursor = start_exclusive + timedelta(days=1)
    while cursor <= end_inclusive:
        if not _is_paused(cursor, pauses):
            days += 1
        cursor += timedelta(days=1)
    return days


async def _calculate_abstinence_streaks(
    db: AsyncSession, owner: User, challenge: Challenge
) -> tuple[int, int]:
    today = _today_for_user(owner)
    started_date = challenge.started_at.astimezone(_user_zone(owner)).date()
    result = await db.execute(
        select(CheckIn.date)
        .where(
            CheckIn.challenge_id == challenge.id,
            CheckIn.owner_id == owner.id,
            CheckIn.is_relapse.is_(True),
        )
        .order_by(CheckIn.date)
    )
    relapses = list(result.scalars().all())
    pauses = await _challenge_pauses(db, owner, challenge)
    last_boundary = relapses[-1] if relapses else started_date
    current = max(_active_elapsed_days(last_boundary, today, pauses), 0)
    boundaries = [started_date, *relapses, today]
    longest = max(
        max(_active_elapsed_days(start, end, pauses), 0)
        for start, end in zip(boundaries, boundaries[1:], strict=False)
    )
    return current, max(current, longest)
