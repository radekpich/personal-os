import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate


async def list_tags(db: AsyncSession, owner: User) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.owner_id == owner.id, Tag.deleted_at.is_(None)).order_by(Tag.name)
    )
    return list(result.scalars().all())


async def get_tag(db: AsyncSession, owner: User, tag_id: uuid.UUID) -> Tag:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.owner_id == owner.id, Tag.deleted_at.is_(None))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tag not found")
    return tag


async def create_tag(db: AsyncSession, owner: User, payload: TagCreate) -> Tag:
    tag = Tag(owner_id=owner.id, name=payload.name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(db: AsyncSession, owner: User, tag_id: uuid.UUID, payload: TagUpdate) -> Tag:
    tag = await get_tag(db, owner, tag_id)
    tag.name = payload.name
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, owner: User, tag_id: uuid.UUID) -> None:
    tag = await get_tag(db, owner, tag_id)
    tag.deleted_at = datetime.now(UTC)
    db.add(tag)
    await db.commit()
