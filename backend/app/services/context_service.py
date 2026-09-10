import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import Context
from app.models.task import Task
from app.models.user import User
from app.schemas.context import ContextCreate, ContextUpdate


async def _task_counts(db: AsyncSession, owner: User) -> dict[uuid.UUID, int]:
    result = await db.execute(
        select(Task.context_id, func.count(Task.id))
        .where(Task.owner_id == owner.id, Task.deleted_at.is_(None), Task.context_id.is_not(None))
        .group_by(Task.context_id)
    )
    return {context_id: count for context_id, count in result.all() if context_id is not None}


def _with_count(context: Context, counts: dict[uuid.UUID, int]) -> Context:
    context.task_count = counts.get(context.id, 0)  # type: ignore[attr-defined]
    return context


async def list_contexts(db: AsyncSession, owner: User) -> list[Context]:
    result = await db.execute(
        select(Context)
        .where(Context.owner_id == owner.id, Context.deleted_at.is_(None))
        .order_by(Context.position, Context.name)
    )
    counts = await _task_counts(db, owner)
    return [_with_count(context, counts) for context in result.scalars().all()]


async def get_context(db: AsyncSession, owner: User, context_id: uuid.UUID) -> Context:
    result = await db.execute(
        select(Context).where(
            Context.id == context_id,
            Context.owner_id == owner.id,
            Context.deleted_at.is_(None),
        )
    )
    context = result.scalar_one_or_none()
    if context is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="context not found")
    counts = await _task_counts(db, owner)
    return _with_count(context, counts)


async def create_context(db: AsyncSession, owner: User, payload: ContextCreate) -> Context:
    context = Context(
        owner_id=owner.id,
        name=payload.name,
        color=payload.color,
        icon=payload.icon,
        position=payload.position,
        is_archived=payload.is_archived,
    )
    db.add(context)
    await db.commit()
    await db.refresh(context)
    return _with_count(context, {})


async def update_context(
    db: AsyncSession, owner: User, context_id: uuid.UUID, payload: ContextUpdate
) -> Context:
    context = await get_context(db, owner, context_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(context, field, value)
    db.add(context)
    await db.commit()
    await db.refresh(context)
    return await get_context(db, owner, context.id)


async def delete_context(db: AsyncSession, owner: User, context_id: uuid.UUID) -> None:
    context = await get_context(db, owner, context_id)
    if context.task_count > 0:  # type: ignore[attr-defined]
        context.is_archived = True
        db.add(context)
    else:
        await db.execute(delete(Context).where(Context.id == context.id))
    await db.commit()
