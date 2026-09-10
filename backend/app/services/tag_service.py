import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.task import task_tags
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate


async def _task_counts(db: AsyncSession, owner: User) -> dict[uuid.UUID, int]:
    result = await db.execute(
        select(task_tags.c.tag_id, func.count(task_tags.c.task_id))
        .join(Tag, Tag.id == task_tags.c.tag_id)
        .where(Tag.owner_id == owner.id, Tag.deleted_at.is_(None))
        .group_by(task_tags.c.tag_id)
    )
    return {tag_id: count for tag_id, count in result.all()}


def _with_count(tag: Tag, counts: dict[uuid.UUID, int]) -> Tag:
    tag.task_count = counts.get(tag.id, 0)  # type: ignore[attr-defined]
    return tag


async def list_tags(db: AsyncSession, owner: User) -> list[Tag]:
    result = await db.execute(
        select(Tag)
        .where(Tag.owner_id == owner.id, Tag.deleted_at.is_(None))
        .order_by(Tag.position, Tag.name)
    )
    counts = await _task_counts(db, owner)
    return [_with_count(tag, counts) for tag in result.scalars().all()]


async def get_tag(db: AsyncSession, owner: User, tag_id: uuid.UUID) -> Tag:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.owner_id == owner.id, Tag.deleted_at.is_(None))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tag not found")
    counts = await _task_counts(db, owner)
    return _with_count(tag, counts)


async def create_tag(db: AsyncSession, owner: User, payload: TagCreate) -> Tag:
    tag = Tag(
        owner_id=owner.id,
        name=payload.name,
        color=payload.color,
        icon=payload.icon,
        position=payload.position,
        is_archived=payload.is_archived,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return _with_count(tag, {})


async def update_tag(db: AsyncSession, owner: User, tag_id: uuid.UUID, payload: TagUpdate) -> Tag:
    tag = await get_tag(db, owner, tag_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(tag, field, value)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return await get_tag(db, owner, tag.id)


async def delete_tag(db: AsyncSession, owner: User, tag_id: uuid.UUID) -> None:
    tag = await get_tag(db, owner, tag_id)
    if tag.task_count > 0:  # type: ignore[attr-defined]
        tag.is_archived = True
        db.add(tag)
    else:
        await db.execute(delete(Tag).where(Tag.id == tag.id))
    await db.commit()
