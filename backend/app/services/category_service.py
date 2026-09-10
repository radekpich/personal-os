import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.task import Task
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate


async def _task_counts(db: AsyncSession, owner: User) -> dict[uuid.UUID, int]:
    result = await db.execute(
        select(Task.category_id, func.count(Task.id))
        .where(Task.owner_id == owner.id, Task.deleted_at.is_(None), Task.category_id.is_not(None))
        .group_by(Task.category_id)
    )
    return {category_id: count for category_id, count in result.all() if category_id is not None}


def _with_count(category: Category, counts: dict[uuid.UUID, int]) -> Category:
    category.task_count = counts.get(category.id, 0)  # type: ignore[attr-defined]
    return category


async def list_categories(db: AsyncSession, owner: User) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.owner_id == owner.id, Category.deleted_at.is_(None))
        .order_by(Category.position, Category.name)
    )
    counts = await _task_counts(db, owner)
    return [_with_count(category, counts) for category in result.scalars().all()]


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
    counts = await _task_counts(db, owner)
    return _with_count(category, counts)


async def _validate_parent(
    db: AsyncSession, owner: User, parent_id: uuid.UUID | None, category_id: uuid.UUID | None = None
) -> uuid.UUID | None:
    if parent_id is None:
        return None
    if category_id is not None and parent_id == category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="category cannot be its own parent"
        )
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
    return _with_count(category, {})


async def update_category(
    db: AsyncSession, owner: User, category_id: uuid.UUID, payload: CategoryUpdate
) -> Category:
    category = await get_category(db, owner, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        category.parent_id = await _validate_parent(db, owner, payload.parent_id, category_id)
    for field in ("name", "color", "icon", "position", "is_archived"):
        if field in changes:
            setattr(category, field, changes[field])
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return await get_category(db, owner, category.id)


async def delete_category(db: AsyncSession, owner: User, category_id: uuid.UUID) -> None:
    category = await get_category(db, owner, category_id)
    child_count = (
        await db.execute(
            select(func.count(Category.id)).where(
                Category.owner_id == owner.id,
                Category.parent_id == category_id,
                Category.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    if category.task_count > 0 or child_count > 0:  # type: ignore[attr-defined]
        category.is_archived = True
        db.add(category)
    else:
        await db.execute(delete(Category).where(Category.id == category.id))
    await db.commit()
