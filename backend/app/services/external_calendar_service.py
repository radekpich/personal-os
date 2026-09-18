import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.external_calendar import (
    CalendarRequest,
    CalendarRequestOperation,
    CalendarRequestStatus,
    ExternalCalendar,
)
from app.models.task import Task
from app.models.user import User
from app.schemas.external_calendar import (
    CalendarRequestComplete,
    CalendarRequestCreate,
    CalendarRequestRead,
    ExternalCalendarSyncRequest,
    ExternalCalendarUpdate,
)


def _now() -> datetime:
    return datetime.now(UTC)


PRAGUE_TZ = ZoneInfo("Europe/Prague")


def _local_dt(task: Task) -> datetime | None:
    if task.due_date is None:
        return None
    return datetime.combine(task.due_date, task.due_time or time(9, 0)).replace(tzinfo=PRAGUE_TZ)


def _calendar_description(task: Task) -> str:
    parts = [task.description or "", "", f"Personal OS task: /tasks?task={task.id}"]
    return "\n".join(part for part in parts if part is not None).strip()


async def list_calendars(db: AsyncSession, owner: User) -> list[ExternalCalendar]:
    result = await db.execute(
        select(ExternalCalendar)
        .where(ExternalCalendar.owner_id == owner.id)
        .order_by(
            ExternalCalendar.is_default.desc(),
            ExternalCalendar.is_primary.desc(),
            ExternalCalendar.name,
        )
    )
    return list(result.scalars().all())


async def sync_calendars(
    db: AsyncSession, owner_id: uuid.UUID, payload: ExternalCalendarSyncRequest
) -> list[ExternalCalendar]:
    synced_at = _now()
    incoming = {item.external_id: item for item in payload.calendars}
    result = await db.execute(select(ExternalCalendar).where(ExternalCalendar.owner_id == owner_id))
    existing = {calendar.external_id: calendar for calendar in result.scalars().all()}
    default_external_id = next(
        (item.external_id for item in payload.calendars if item.is_default and item.can_write), None
    )
    calendars: list[ExternalCalendar] = []
    for item in payload.calendars:
        calendar = existing.get(item.external_id)
        if calendar is None:
            calendar = ExternalCalendar(owner_id=owner_id, external_id=item.external_id)
        calendar.name = item.name
        calendar.color = item.color
        calendar.can_write = item.can_write
        calendar.is_shared = item.is_shared
        calendar.is_primary = item.is_primary
        calendar.is_enabled = item.is_enabled and item.can_write
        calendar.is_default = (
            item.is_default and item.can_write and item.external_id == default_external_id
        )
        calendar.last_synced_at = synced_at
        db.add(calendar)
        calendars.append(calendar)
    for external_id, calendar in existing.items():
        if external_id not in incoming:
            await db.delete(calendar)
    if default_external_id is None:
        for calendar in calendars:
            calendar.is_default = False
        first_writeable = next((calendar for calendar in calendars if calendar.can_write), None)
        if first_writeable is not None:
            first_writeable.is_default = True
    await db.commit()
    return await list_calendars_for_owner_id(db, owner_id)


async def list_calendars_for_owner_id(
    db: AsyncSession, owner_id: uuid.UUID
) -> list[ExternalCalendar]:
    result = await db.execute(
        select(ExternalCalendar)
        .where(ExternalCalendar.owner_id == owner_id)
        .order_by(ExternalCalendar.name)
    )
    return list(result.scalars().all())


async def update_calendar(
    db: AsyncSession, owner: User, calendar_id: uuid.UUID, payload: ExternalCalendarUpdate
) -> ExternalCalendar:
    result = await db.execute(
        select(ExternalCalendar).where(
            ExternalCalendar.owner_id == owner.id, ExternalCalendar.id == calendar_id
        )
    )
    calendar = result.scalar_one_or_none()
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="calendar not found")
    if payload.is_enabled is not None:
        calendar.is_enabled = payload.is_enabled and calendar.can_write
    if payload.is_default is True:
        if not calendar.can_write:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="calendar is read-only"
            )
        await db.execute(
            sa.update(ExternalCalendar)
            .where(ExternalCalendar.owner_id == owner.id)
            .values(is_default=False)
        )
        calendar.is_default = True
        calendar.is_enabled = True
    elif payload.is_default is False:
        calendar.is_default = False
    db.add(calendar)
    await db.commit()
    await db.refresh(calendar)
    return calendar


async def _get_writeable_calendar(
    db: AsyncSession, owner: User, external_id: str
) -> ExternalCalendar:
    result = await db.execute(
        select(ExternalCalendar).where(
            ExternalCalendar.owner_id == owner.id,
            ExternalCalendar.external_id == external_id,
            ExternalCalendar.can_write.is_(True),
            ExternalCalendar.is_enabled.is_(True),
        )
    )
    calendar = result.scalar_one_or_none()
    if calendar is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="calendar is not available for tasks"
        )
    return calendar


async def _task(db: AsyncSession, owner: User, task_id: uuid.UUID) -> Task:
    result = await db.execute(
        select(Task).where(Task.owner_id == owner.id, Task.id == task_id, Task.deleted_at.is_(None))
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return task


async def create_request(
    db: AsyncSession, owner: User, task_id: uuid.UUID, payload: CalendarRequestCreate
) -> CalendarRequest:
    existing = (
        await db.execute(
            select(CalendarRequest).where(
                CalendarRequest.owner_id == owner.id,
                CalendarRequest.idempotency_key == payload.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    task = await _task(db, owner, task_id)
    calendar = await _get_writeable_calendar(db, owner, payload.calendar_external_id)
    title = payload.title or task.title
    request = CalendarRequest(
        owner_id=owner.id,
        task_id=task.id,
        operation=payload.operation.value,
        calendar_external_id=calendar.external_id,
        title=title,
        description=payload.description
        if payload.description is not None
        else _calendar_description(task),
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        all_day=payload.all_day,
        reminder_minutes=payload.reminder_minutes,
        idempotency_key=payload.idempotency_key,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


async def latest_request_for_task(
    db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID
) -> CalendarRequest | None:
    result = await db.execute(
        select(CalendarRequest)
        .where(CalendarRequest.owner_id == owner_id, CalendarRequest.task_id == task_id)
        .order_by(CalendarRequest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def latest_done_request_for_task(db: AsyncSession, task: Task) -> CalendarRequest | None:
    result = await db.execute(
        select(CalendarRequest)
        .where(
            CalendarRequest.owner_id == task.owner_id,
            CalendarRequest.task_id == task.id,
            CalendarRequest.status == CalendarRequestStatus.DONE.value,
            CalendarRequest.external_event_id.is_not(None),
        )
        .order_by(CalendarRequest.completed_at.desc(), CalendarRequest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def task_has_external_calendar_event_clause() -> sa.Exists:
    return sa.exists(
        select(CalendarRequest.id).where(
            CalendarRequest.task_id == Task.id,
            CalendarRequest.owner_id == Task.owner_id,
            CalendarRequest.status.in_(
                [
                    CalendarRequestStatus.PENDING.value,
                    CalendarRequestStatus.CLAIMED.value,
                    CalendarRequestStatus.DONE.value,
                ]
            ),
            CalendarRequest.operation != CalendarRequestOperation.DELETE.value,
        )
    )


async def serialize_request(db: AsyncSession, request: CalendarRequest) -> CalendarRequestRead:
    result = await db.execute(
        select(ExternalCalendar).where(
            ExternalCalendar.owner_id == request.owner_id,
            ExternalCalendar.external_id == request.calendar_external_id,
        )
    )
    calendar = result.scalar_one_or_none()
    data = CalendarRequestRead.model_validate(request)
    data.calendar_name = calendar.name if calendar else None
    data.calendar_color = calendar.color if calendar else None
    return data


async def cancel_request(db: AsyncSession, owner: User, request_id: uuid.UUID) -> CalendarRequest:
    request = await _owned_request(db, owner, request_id)
    if request.status != CalendarRequestStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="only pending requests can be cancelled"
        )
    request.status = CalendarRequestStatus.CANCELLED.value
    await db.commit()
    await db.refresh(request)
    return request


async def disconnect_request(
    db: AsyncSession, owner: User, request_id: uuid.UUID
) -> CalendarRequest:
    request = await _owned_request(db, owner, request_id)
    if request.status != CalendarRequestStatus.DONE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="only done requests can be disconnected"
        )
    request.status = CalendarRequestStatus.CANCELLED.value
    await db.commit()
    await db.refresh(request)
    return request


async def retry_request(db: AsyncSession, owner: User, request_id: uuid.UUID) -> CalendarRequest:
    request = await _owned_request(db, owner, request_id)
    if request.status != CalendarRequestStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="only failed requests can be retried"
        )
    request.status = CalendarRequestStatus.PENDING.value
    request.claimed_at = None
    request.claimed_by = None
    request.error_message = None
    await db.commit()
    await db.refresh(request)
    return request


async def _owned_request(db: AsyncSession, owner: User, request_id: uuid.UUID) -> CalendarRequest:
    result = await db.execute(
        select(CalendarRequest).where(
            CalendarRequest.owner_id == owner.id, CalendarRequest.id == request_id
        )
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="calendar request not found"
        )
    return request


async def pending_requests(
    db: AsyncSession, owner_id: uuid.UUID, status_filter: CalendarRequestStatus
) -> list[CalendarRequest]:
    result = await db.execute(
        select(CalendarRequest)
        .where(CalendarRequest.owner_id == owner_id, CalendarRequest.status == status_filter.value)
        .order_by(CalendarRequest.created_at)
    )
    return list(result.scalars().all())


async def claim_request(
    db: AsyncSession, owner_id: uuid.UUID, request_id: uuid.UUID, api_key_id: uuid.UUID
) -> CalendarRequest:
    result = await db.execute(
        sa.update(CalendarRequest)
        .where(
            CalendarRequest.owner_id == owner_id,
            CalendarRequest.id == request_id,
            CalendarRequest.status == CalendarRequestStatus.PENDING.value,
        )
        .values(
            status=CalendarRequestStatus.CLAIMED.value, claimed_at=_now(), claimed_by=api_key_id
        )
        .returning(CalendarRequest)
    )
    request = result.scalar_one_or_none()
    if request is None:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="calendar request already claimed"
        )
    await db.commit()
    return request


async def complete_request(
    db: AsyncSession, owner_id: uuid.UUID, request_id: uuid.UUID, payload: CalendarRequestComplete
) -> CalendarRequest:
    result = await db.execute(
        select(CalendarRequest).where(
            CalendarRequest.owner_id == owner_id, CalendarRequest.id == request_id
        )
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="calendar request not found"
        )
    if request.status != CalendarRequestStatus.CLAIMED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="calendar request is not claimed"
        )
    request.completed_at = _now()
    request.external_event_id = payload.external_event_id
    request.external_event_link = payload.external_event_link
    request.error_message = payload.error_message
    request.status = (
        CalendarRequestStatus.FAILED.value
        if payload.error_message
        else CalendarRequestStatus.DONE.value
    )
    await db.commit()
    await db.refresh(request)
    return request


async def release_stale_claims(sessionmaker: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    cutoff = _now() - timedelta(minutes=5)
    async with sessionmaker() as db:
        result = await db.execute(
            select(CalendarRequest).where(
                CalendarRequest.status == CalendarRequestStatus.CLAIMED.value,
                CalendarRequest.claimed_at < cutoff,
            )
        )
        requests = list(result.scalars().all())
        pending = failed = 0
        for request in requests:
            request.attempt_count += 1
            request.claimed_at = None
            request.claimed_by = None
            if request.attempt_count >= 3:
                request.status = CalendarRequestStatus.FAILED.value
                request.error_message = "Agent request timed out three times"
                failed += 1
            else:
                request.status = CalendarRequestStatus.PENDING.value
                pending += 1
        await db.commit()
        return {"released": pending, "failed": failed}


async def enqueue_update_for_task(
    db: AsyncSession, task: Task, *, completed_marker: bool = False
) -> None:
    linked = await latest_done_request_for_task(db, task)
    if linked is None:
        return
    start = _local_dt(task) or linked.starts_at
    end = start + (
        linked.ends_at - linked.starts_at
        if linked.ends_at > linked.starts_at
        else timedelta(minutes=task.estimate_minutes or 30)
    )
    title = f"✅ {task.title}" if completed_marker else task.title
    request = CalendarRequest(
        owner_id=task.owner_id,
        task_id=task.id,
        operation=CalendarRequestOperation.UPDATE.value,
        calendar_external_id=linked.calendar_external_id,
        title=title,
        description=_calendar_description(task),
        starts_at=start,
        ends_at=end,
        all_day=task.due_time is None,
        reminder_minutes=linked.reminder_minutes,
        external_event_id=linked.external_event_id,
        external_event_link=linked.external_event_link,
        idempotency_key=f"auto-update-{task.id}-{task.version + 1}-{uuid.uuid4()}",
    )
    db.add(request)


async def enqueue_delete_for_task(db: AsyncSession, task: Task) -> None:
    linked = await latest_done_request_for_task(db, task)
    if linked is None:
        return
    request = CalendarRequest(
        owner_id=task.owner_id,
        task_id=task.id,
        operation=CalendarRequestOperation.DELETE.value,
        calendar_external_id=linked.calendar_external_id,
        title=task.title,
        description=_calendar_description(task),
        starts_at=linked.starts_at,
        ends_at=linked.ends_at,
        all_day=linked.all_day,
        reminder_minutes=linked.reminder_minutes,
        external_event_id=linked.external_event_id,
        external_event_link=linked.external_event_link,
        idempotency_key=f"auto-delete-{task.id}-{uuid.uuid4()}",
    )
    db.add(request)
