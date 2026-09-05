import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.vision import Vision
from app.schemas.vision import VisionCreate, VisionUpdate
from app.services import category_service


async def list_visions(db: AsyncSession, owner: User) -> list[Vision]:
    result = await db.execute(
        select(Vision)
        .where(Vision.owner_id == owner.id, Vision.deleted_at.is_(None))
        .order_by(Vision.position, Vision.created_at)
    )
    return list(result.scalars().all())


async def get_vision(db: AsyncSession, owner: User, vision_id: uuid.UUID) -> Vision:
    result = await db.execute(
        select(Vision).where(
            Vision.id == vision_id,
            Vision.owner_id == owner.id,
            Vision.deleted_at.is_(None),
        )
    )
    vision = result.scalar_one_or_none()
    if vision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vision not found")
    return vision


async def _validate_links(
    db: AsyncSession,
    owner: User,
    parent_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
) -> None:
    if parent_id is not None:
        await get_vision(db, owner, parent_id)
    if category_id is not None:
        await category_service.get_category(db, owner, category_id)


async def create_vision(db: AsyncSession, owner: User, payload: VisionCreate) -> Vision:
    await _validate_links(db, owner, payload.parent_id, payload.category_id)
    vision = Vision(
        owner_id=owner.id,
        title=payload.title,
        description=payload.description,
        parent_id=payload.parent_id,
        horizon=payload.horizon.value,
        status=payload.status.value,
        target_date=payload.target_date,
        category_id=payload.category_id,
        position=payload.position,
    )
    db.add(vision)
    await db.commit()
    await db.refresh(vision)
    return vision


async def update_vision(
    db: AsyncSession, owner: User, vision_id: uuid.UUID, payload: VisionUpdate
) -> Vision:
    vision = await get_vision(db, owner, vision_id)
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes or "category_id" in changes:
        await _validate_links(
            db,
            owner,
            payload.parent_id if "parent_id" in changes else vision.parent_id,
            payload.category_id if "category_id" in changes else vision.category_id,
        )
    for field in ("title", "description", "parent_id", "target_date", "category_id", "position"):
        if field in changes:
            setattr(vision, field, changes[field])
    if "horizon" in changes and payload.horizon is not None:
        vision.horizon = payload.horizon.value
    if "status" in changes and payload.status is not None:
        vision.status = payload.status.value
    db.add(vision)
    await db.commit()
    await db.refresh(vision)
    return vision


async def delete_vision(db: AsyncSession, owner: User, vision_id: uuid.UUID) -> None:
    vision = await get_vision(db, owner, vision_id)
    vision.deleted_at = datetime.now(UTC)
    db.add(vision)
    await db.commit()
