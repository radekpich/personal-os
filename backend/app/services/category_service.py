import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate


async def list_categories(db: AsyncSession, owner: User) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.owner_id == owner.id, Category.deleted_at.is_(None))
        .order_by(Category.position, Category.name)
    )
    return list(result.scalars().all())


async def get_category(db: AsyncSession, owner: User, category_id: uuid.UUID) -> Category:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.owner_id == owner.id,
            Category.deleted_at.is_(None),
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
    return category


async def _validate_parent(
    db: AsyncSession, owner: User, parent_id: uuid.UUID | None
) -> uuid.UUID | None:
    if parent_id is None:
        return None
    parent = await get_category(db, owner, parent_id)
    if parent.parent_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="categories support only two levels",
        )
    return parent.id


async def create_category(db: AsyncSession, owner: User, payload: CategoryCreate) -> Category:
    parent_id = await _validate_parent(db, owner, payload.parent_id)
    category = Category(
        owner_id=owner.id,
        name=payload.name,
        color=payload.color,
        icon=payload.icon,
        parent_id=parent_id,
        position=payload.position,
        is_archived=payload.is_archived,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession, owner: User, category_id: uuid.UUID, payload: CategoryUpdate
) -> Category:
    category = await get_category(db, owner, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        category.parent_id = await _validate_parent(db, owner, payload.parent_id)
    for field in ("name", "color", "icon", "position", "is_archived"):
        if field in changes:
            setattr(category, field, changes[field])
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, owner: User, category_id: uuid.UUID) -> None:
    category = await get_category(db, owner, category_id)
    category.deleted_at = datetime.now(UTC)
    db.add(category)
    await db.commit()
