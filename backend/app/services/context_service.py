import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import Context
from app.models.user import User
from app.schemas.context import ContextCreate, ContextUpdate


async def list_contexts(db: AsyncSession, owner: User) -> list[Context]:
    result = await db.execute(
        select(Context)
        .where(Context.owner_id == owner.id, Context.deleted_at.is_(None))
        .order_by(Context.position, Context.name)
    )
    return list(result.scalars().all())


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
    return context


async def create_context(db: AsyncSession, owner: User, payload: ContextCreate) -> Context:
    context = Context(
        owner_id=owner.id,
        name=payload.name,
        position=payload.position,
        is_archived=payload.is_archived,
    )
    db.add(context)
    await db.commit()
    await db.refresh(context)
    return context


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
    return context


async def delete_context(db: AsyncSession, owner: User, context_id: uuid.UUID) -> None:
    context = await get_context(db, owner, context_id)
    context.deleted_at = datetime.now(UTC)
    db.add(context)
    await db.commit()
