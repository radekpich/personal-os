import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note, NoteKind
from app.models.user import User
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.services import category_service, task_service, vision_service
from app.services.concurrency import (
    MutationActor,
    apply_mutation_audit,
    ensure_can_mutate,
    state_from_schema,
)


@dataclass(frozen=True)
class NoteListFilters:
    kind: NoteKind | None = None
    entry_date: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None
    category_id: uuid.UUID | None = None
    vision_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    page: int = 1
    page_size: int = 20


async def _validate_links(
    db: AsyncSession,
    owner: User,
    category_id: uuid.UUID | None,
    vision_id: uuid.UUID | None,
    task_id: uuid.UUID | None,
) -> None:
    if category_id is not None:
        await category_service.get_category(db, owner, category_id)
    if vision_id is not None:
        await vision_service.get_vision(db, owner, vision_id)
    if task_id is not None:
        await task_service.get_task(db, owner, task_id)


def _filtered_notes_query(owner: User, filters: NoteListFilters) -> Select[tuple[Note]]:
    query = select(Note).where(Note.owner_id == owner.id, Note.deleted_at.is_(None))
    if filters.kind is not None:
        query = query.where(Note.kind == filters.kind.value)
    if filters.entry_date is not None:
        query = query.where(Note.entry_date == filters.entry_date)
    if filters.date_from is not None:
        query = query.where(Note.entry_date >= filters.date_from)
    if filters.date_to is not None:
        query = query.where(Note.entry_date <= filters.date_to)
    if filters.category_id is not None:
        query = query.where(Note.category_id == filters.category_id)
    if filters.vision_id is not None:
        query = query.where(Note.vision_id == filters.vision_id)
    if filters.task_id is not None:
        query = query.where(Note.task_id == filters.task_id)
    if filters.q:
        pattern = f"%{filters.q.strip()}%"
        query = query.where(or_(Note.title.ilike(pattern), Note.body.ilike(pattern)))
    return query


async def list_notes(
    db: AsyncSession, owner: User, filters: NoteListFilters
) -> tuple[list[Note], int]:
    base_query = _filtered_notes_query(owner, filters)
    total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    result = await db.execute(
        base_query.order_by(Note.entry_date.desc().nullslast(), Note.created_at.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    return list(result.scalars().all()), int(total or 0)


async def get_note(db: AsyncSession, owner: User, note_id: uuid.UUID) -> Note:
    result = await db.execute(
        select(Note).where(
            Note.id == note_id,
            Note.owner_id == owner.id,
            Note.deleted_at.is_(None),
        )
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note not found")
    return note


async def create_note(
    db: AsyncSession,
    owner: User,
    payload: NoteCreate,
    *,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
) -> Note:
    await _validate_links(db, owner, payload.category_id, payload.vision_id, payload.task_id)
    note = Note(
        owner_id=owner.id,
        title=payload.title,
        body=payload.body,
        kind=payload.kind.value,
        entry_date=payload.entry_date,
        entry_time=payload.entry_time,
        mood=payload.mood,
        category_id=payload.category_id,
        vision_id=payload.vision_id,
        task_id=payload.task_id,
        version=1,
        created_by=actor.value,
        updated_by=actor.value,
        api_key_id=api_key_id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def update_note(
    db: AsyncSession,
    owner: User,
    note_id: uuid.UUID,
    payload: NoteUpdate,
    *,
    expected_version: int | None = None,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
    fresh_user_edit_guard_minutes: int = 5,
) -> Note:
    note = await get_note(db, owner, note_id)
    ensure_can_mutate(
        note,
        expected_version=expected_version,
        actor=actor,
        current_state=state_from_schema(NoteRead, note),
        fresh_user_edit_guard_minutes=fresh_user_edit_guard_minutes,
    )
    changes = payload.model_dump(exclude_unset=True)
    category_id = changes.get("category_id", note.category_id)
    vision_id = changes.get("vision_id", note.vision_id)
    task_id = changes.get("task_id", note.task_id)
    if {"category_id", "vision_id", "task_id"} & set(changes):
        await _validate_links(db, owner, category_id, vision_id, task_id)

    for field in (
        "title",
        "body",
        "entry_date",
        "entry_time",
        "mood",
        "category_id",
        "vision_id",
        "task_id",
    ):
        if field in changes:
            setattr(note, field, changes[field])
    if "kind" in changes and payload.kind is not None:
        note.kind = payload.kind.value

    apply_mutation_audit(note, actor=actor, api_key_id=api_key_id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(
    db: AsyncSession,
    owner: User,
    note_id: uuid.UUID,
    *,
    expected_version: int | None = None,
    actor: MutationActor = MutationActor.USER,
    api_key_id: uuid.UUID | None = None,
    fresh_user_edit_guard_minutes: int = 5,
) -> None:
    note = await get_note(db, owner, note_id)
    ensure_can_mutate(
        note,
        expected_version=expected_version,
        actor=actor,
        current_state=state_from_schema(NoteRead, note),
        fresh_user_edit_guard_minutes=fresh_user_edit_guard_minutes,
    )
    note.deleted_at = datetime.now(UTC)
    apply_mutation_audit(note, actor=actor, api_key_id=api_key_id)
    db.add(note)
    await db.commit()
