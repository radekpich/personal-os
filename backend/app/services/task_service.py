import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.task import RecurrenceMode, Task, TaskPriority, TaskSource, TaskStatus, task_tags
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate, TaskView
from app.services import category_service, context_service, vision_service
from app.services.concurrency import (
    MutationActor,
    apply_mutation_audit,
    ensure_can_mutate,
    state_from_schema,
)

LOCAL_TIMEZONE = ZoneInfo("Europe/Prague")
WEEKDAY_TO_INDEX = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _parse_rrule(rrule: str) -> dict[str, str]:
    return dict(part.split("=", 1) for part in rrule.split(";") if "=" in part)


def _next_due_date(rrule: str, mode: str, task: Task, completed_at: datetime) -> date | None:
    parts = _parse_rrule(rrule)
    interval = int(parts.get("INTERVAL", "1"))
    if mode == RecurrenceMode.AFTER_COMPLETION.value:
        anchor = completed_at.astimezone(LOCAL_TIMEZONE).date()
    else:
        anchor = task.due_date or completed_at.astimezone(LOCAL_TIMEZONE).date()

    freq = parts["FREQ"]
    if freq == "DAILY":
        return anchor + timedelta(days=interval)
    if freq == "WEEKLY":
        byday = parts.get("BYDAY")
        if byday:
            targets = [
                WEEKDAY_TO_INDEX[item] for item in byday.split(",") if item in WEEKDAY_TO_INDEX
            ]
            for offset in range(1, 7 * interval + 8):
                candidate = anchor + timedelta(days=offset)
                if candidate.weekday() in targets:
                    return candidate
        return anchor + timedelta(weeks=interval)
    if freq == "MONTHLY":
        month = anchor.month - 1 + interval
        year = anchor.year + month // 12
        month = month % 12 + 1
        day = min(anchor.day, 28)
        return date(year, month, day)
    if freq == "YEARLY":
        return date(anchor.year + interval, anchor.month, min(anchor.day, 28))
    return None


async def _generate_next_recurrence_instance(
    db: AsyncSession, task: Task, completed_at: datetime
) -> None:
    if task.recurrence_rule is None or task.recurrence_mode is None:
        return
    template_id = task.recurrence_template_id or task.id
    next_due = _next_due_date(task.recurrence_rule, task.recurrence_mode, task, completed_at)
    if next_due is None:
        return
    existing = await db.execute(
        select(Task).where(
            Task.owner_id == task.owner_id,
            Task.recurrence_template_id == template_id,
            Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value]),
            Task.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    next_task = Task(
        owner_id=task.owner_id,
        title=task.title,
        description=task.description,
        status=TaskStatus.TODO.value,
        priority=task.priority,
        due_date=next_due,
        due_time=task.due_time,
        estimate_minutes=task.estimate_minutes,
        category_id=task.category_id,
        context_id=task.context_id,
        vision_id=task.vision_id,
        parent_task_id=task.parent_task_id,
        recurrence_template_id=template_id,
        recurrence_rule=task.recurrence_rule,
        recurrence_mode=task.recurrence_mode,
        position=task.position,
        tags=list(task.tags),
    )
    db.add(next_task)


@dataclass
class TaskListFilters:
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    category_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] | None = None
    due_from: date | None = None
    due_to: date | None = None
    q: str | None = None
    view: TaskView | None = None
    source: TaskSource | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    page: int = 1
    page_size: int = 20


def _local_today() -> date:
    return datetime.now(LOCAL_TIMEZONE).date()


def _view_condition(view: TaskView) -> sa.ColumnElement[bool]:
    today = _local_today()
    if view == TaskView.INBOX:
        return sa.or_(Task.category_id.is_(None), Task.context_id.is_(None))
    if view == TaskView.TODAY:
        return Task.due_date == today
    if view == TaskView.TOMORROW:
        return Task.due_date == today + timedelta(days=1)
    if view == TaskView.UNSCHEDULED:
        return Task.due_date.is_(None)
    if view == TaskView.THIS_WEEK:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return sa.and_(Task.due_date >= start, Task.due_date <= end)
    return sa.and_(
        Task.due_date < today,
        Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value]),
    )


def _build_conditions(owner: User, filters: TaskListFilters) -> list[sa.ColumnElement[bool]]:
    conditions: list[sa.ColumnElement[bool]] = [
        Task.owner_id == owner.id,
        Task.deleted_at.is_(None),
    ]
    if filters.status is not None:
        conditions.append(Task.status == filters.status.value)
    if filters.priority is not None:
        conditions.append(Task.priority == filters.priority.value)
    if filters.category_id is not None:
        conditions.append(Task.category_id == filters.category_id)
    if filters.context_id is not None:
        conditions.append(Task.context_id == filters.context_id)
    if filters.vision_id is not None:
        conditions.append(Task.vision_id == filters.vision_id)
    if filters.tag_ids:
        conditions.append(
            Task.id.in_(select(task_tags.c.task_id).where(task_tags.c.tag_id.in_(filters.tag_ids)))
        )
    if filters.due_from is not None:
        conditions.append(Task.due_date >= filters.due_from)
    if filters.due_to is not None:
        conditions.append(Task.due_date <= filters.due_to)
    if filters.q:
        pattern = f"%{filters.q}%"
        conditions.append(sa.or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
    if filters.source is not None:
        conditions.append(Task.source == filters.source.value)
    if filters.created_from is not None:
        conditions.append(Task.created_at >= filters.created_from)
    if filters.created_to is not None:
        conditions.append(Task.created_at <= filters.created_to)
    if filters.view is not None:
        conditions.append(_view_condition(filters.view))
        if filters.view != TaskView.INBOX:
            conditions.append(Task.category_id.is_not(None))
            conditions.append(Task.context_id.is_not(None))
    elif filters.status is None and filters.vision_id is None:
        conditions.append(Task.category_id.is_not(None))
        conditions.append(Task.context_id.is_not(None))
    return conditions


async def list_tasks(
    db: AsyncSession, owner: User, filters: TaskListFilters
) -> tuple[list[Task], int]:
    conditions = _build_conditions(owner, filters)

    total = (
        await db.execute(select(sa.func.count()).select_from(Task).where(*conditions))
    ).scalar_one()

    priority_order = sa.case(
        (Task.priority == TaskPriority.HIGH.value, 0),
        (Task.priority == TaskPriority.MEDIUM.value, 1),
        (Task.priority == TaskPriority.LOW.value, 2),
        else_=3,
    )
    if filters.view == TaskView.INBOX:
        order_by = (Task.created_at.desc(),)
    elif filters.view in {TaskView.TODAY, TaskView.TOMORROW, TaskView.OVERDUE}:
        order_by = (
            Task.due_time.is_(None),
            Task.due_time,
            priority_order,
            Task.position,
            Task.created_at,
        )
    else:
        order_by = (Task.position, Task.created_at)

    stmt = (
        select(Task)
        .where(*conditions)
        .order_by(*order_by)
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    tasks = (await db.execute(stmt)).scalars().all()
    return list(tasks), total


async def get_task(db: AsyncSession, owner: User, task_id: uuid.UUID) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.owner_id == owner.id, Task.deleted_at.is_(None))
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return task


async def _resolve_tags(db: AsyncSession, owner: User, tag_ids: list[uuid.UUID]) -> list[Tag]:
    if not tag_ids:
        return []
    unique_ids = set(tag_ids)
    result = await db.execute(
        select(Tag).where(
            Tag.id.in_(unique_ids), Tag.owner_id == owner.id, Tag.deleted_at.is_(None)
        )
    )
    tags = list(result.scalars().all())
    if len(tags) != len(unique_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tag not found")
    return tags


async def quick_create_task(
    db: AsyncSession,
    owner: User,
    title: str,
    *,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
) -> Task:
    title = title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="title must not be empty"
        )
    if len(title) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title too long")
    task = Task(
        owner_id=owner.id,
        title=title,
        status=TaskStatus.INBOX.value,
        priority=TaskPriority.NONE.value,
        source=(
            TaskSource.QUICK_CAPTURE.value
            if actor == MutationActor.USER
            else TaskSource.AGENT.value
        ),
        version=1,
        created_by=actor.value,
        updated_by=actor.value,
        api_key_id=api_key_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def create_task(
    db: AsyncSession,
    owner: User,
    payload: TaskCreate,
    *,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
) -> Task:
    if payload.category_id is not None:
        await category_service.get_category(db, owner, payload.category_id)
    if payload.context_id is not None:
        await context_service.get_context(db, owner, payload.context_id)
    if payload.vision_id is not None:
        await vision_service.get_vision(db, owner, payload.vision_id)
    if payload.parent_task_id is not None:
        await get_task(db, owner, payload.parent_task_id)
    tags = await _resolve_tags(db, owner, payload.tag_ids)

    completed_at = datetime.now(UTC) if payload.status == TaskStatus.DONE else None
    completed_by = actor.value if payload.status == TaskStatus.DONE else None
    task = Task(
        owner_id=owner.id,
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        priority=payload.priority.value,
        due_date=payload.due_date,
        due_time=payload.due_time,
        estimate_minutes=payload.estimate_minutes,
        completed_at=completed_at,
        completed_by=completed_by,
        category_id=payload.category_id,
        context_id=payload.context_id,
        vision_id=payload.vision_id,
        parent_task_id=payload.parent_task_id,
        source=payload.source.value,
        source_detail=payload.source_detail,
        recurrence_rule=payload.recurrence_rule,
        recurrence_mode=payload.recurrence_mode.value
        if payload.recurrence_mode is not None
        else None,
        position=payload.position,
        version=1,
        created_by=actor.value,
        updated_by=actor.value,
        api_key_id=api_key_id,
        tags=tags,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession,
    owner: User,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    *,
    expected_version: int | None = None,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
    fresh_user_edit_guard_minutes: int = 5,
) -> Task:
    task = await get_task(db, owner, task_id)
    ensure_can_mutate(
        task,
        expected_version=expected_version,
        actor=actor,
        current_state=state_from_schema(TaskRead, task),
        fresh_user_edit_guard_minutes=fresh_user_edit_guard_minutes,
    )
    changes = payload.model_dump(exclude_unset=True)

    if "category_id" in changes:
        if payload.category_id is not None:
            await category_service.get_category(db, owner, payload.category_id)
        task.category_id = payload.category_id

    if "context_id" in changes:
        if payload.context_id is not None:
            await context_service.get_context(db, owner, payload.context_id)
        task.context_id = payload.context_id

    if "vision_id" in changes:
        if payload.vision_id is not None:
            await vision_service.get_vision(db, owner, payload.vision_id)
        task.vision_id = payload.vision_id

    if "parent_task_id" in changes:
        if payload.parent_task_id is not None:
            if payload.parent_task_id == task.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="task cannot be its own parent",
                )
            await get_task(db, owner, payload.parent_task_id)
        task.parent_task_id = payload.parent_task_id

    if "tag_ids" in changes:
        task.tags = await _resolve_tags(db, owner, payload.tag_ids or [])

    for field in (
        "title",
        "description",
        "due_date",
        "due_time",
        "estimate_minutes",
        "position",
        "source_detail",
        "recurrence_rule",
    ):
        if field in changes:
            setattr(task, field, changes[field])

    if "source" in changes and payload.source is not None:
        task.source = payload.source.value

    if "recurrence_mode" in changes:
        task.recurrence_mode = (
            payload.recurrence_mode.value if payload.recurrence_mode is not None else None
        )

    if "priority" in changes and payload.priority is not None:
        task.priority = payload.priority.value

    if "status" in changes and payload.status is not None:
        new_status = payload.status
        if new_status == TaskStatus.DONE and task.status != TaskStatus.DONE.value:
            task.completed_at = datetime.now(UTC)
            task.completed_by = actor.value
            await _generate_next_recurrence_instance(db, task, task.completed_at)
        elif new_status != TaskStatus.DONE:
            task.completed_at = None
            task.completed_by = None
        task.status = new_status.value

    apply_mutation_audit(task, actor=actor, api_key_id=api_key_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(
    db: AsyncSession,
    owner: User,
    task_id: uuid.UUID,
    *,
    expected_version: int | None = None,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
    fresh_user_edit_guard_minutes: int = 5,
) -> None:
    task = await get_task(db, owner, task_id)
    ensure_can_mutate(
        task,
        expected_version=expected_version,
        actor=actor,
        current_state=state_from_schema(TaskRead, task),
        fresh_user_edit_guard_minutes=fresh_user_edit_guard_minutes,
    )
    task.deleted_at = datetime.now(UTC)
    apply_mutation_audit(task, actor=actor, api_key_id=api_key_id)
    db.add(task)
    await db.commit()


async def restore_task(
    db: AsyncSession,
    owner: User,
    task_id: uuid.UUID,
    *,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
) -> Task:
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.owner_id == owner.id,
            Task.deleted_at.is_not(None),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    task.deleted_at = None
    apply_mutation_audit(task, actor=actor, api_key_id=api_key_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task
