import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.vision import Vision
from app.schemas.vision import (
    StagnatingVision,
    VisionCreate,
    VisionDeleteImpact,
    VisionProgress,
    VisionRead,
    VisionTreeNode,
    VisionUpdate,
)
from app.services import category_service

MAX_VISION_DEPTH = 4


async def list_visions(db: AsyncSession, owner: User) -> list[Vision]:
    result = await db.execute(
        select(Vision)
        .where(Vision.owner_id == owner.id, Vision.deleted_at.is_(None))
        .order_by(Vision.position, Vision.created_at)
    )
    return list(result.scalars().all())


async def get_vision_tree(db: AsyncSession, owner: User) -> list[VisionTreeNode]:
    visions = await list_visions(db, owner)
    nodes = {vision.id: VisionTreeNode.model_validate(vision) for vision in visions}
    roots: list[VisionTreeNode] = []
    for vision in visions:
        node = nodes[vision.id]
        if vision.parent_id is not None and vision.parent_id in nodes:
            nodes[vision.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


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


async def _load_owner_visions(db: AsyncSession, owner: User) -> dict[uuid.UUID, Vision]:
    result = await db.execute(
        select(Vision).where(Vision.owner_id == owner.id, Vision.deleted_at.is_(None))
    )
    return {vision.id: vision for vision in result.scalars().all()}


def _subtree_height(
    vision_id: uuid.UUID, children_by_parent: dict[uuid.UUID | None, list[Vision]]
) -> int:
    child_heights = [
        _subtree_height(child.id, children_by_parent)
        for child in children_by_parent.get(vision_id, [])
    ]
    return 1 + max(child_heights, default=0)


def _parent_depth(parent_id: uuid.UUID | None, visions_by_id: dict[uuid.UUID, Vision]) -> int:
    depth = 0
    seen: set[uuid.UUID] = set()
    current_id = parent_id
    while current_id is not None:
        if current_id in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="vision parent cycle"
            )
        seen.add(current_id)
        parent = visions_by_id.get(current_id)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="vision parent not found"
            )
        depth += 1
        current_id = parent.parent_id
    return depth


async def _validate_links(
    db: AsyncSession,
    owner: User,
    parent_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    moving_vision_id: uuid.UUID | None = None,
) -> None:
    visions_by_id = await _load_owner_visions(db, owner)
    if parent_id is not None and parent_id not in visions_by_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vision parent not found")
    if moving_vision_id is not None and parent_id == moving_vision_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="vision cannot be its own parent"
        )
    if moving_vision_id is not None and parent_id is not None:
        current_id: uuid.UUID | None = parent_id
        seen: set[uuid.UUID] = set()
        while current_id is not None:
            if current_id in seen or current_id == moving_vision_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="vision parent cycle"
                )
            seen.add(current_id)
            current = visions_by_id[current_id]
            current_id = current.parent_id

    children_by_parent: dict[uuid.UUID | None, list[Vision]] = {}
    for vision in visions_by_id.values():
        if moving_vision_id is not None and vision.id == moving_vision_id:
            continue
        children_by_parent.setdefault(vision.parent_id, []).append(vision)
    subtree_height = (
        _subtree_height(moving_vision_id, children_by_parent) if moving_vision_id else 1
    )
    if _parent_depth(parent_id, visions_by_id) + subtree_height > MAX_VISION_DEPTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="vision tree depth exceeded"
        )

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
            moving_vision_id=vision.id,
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


async def get_vision_progress(
    db: AsyncSession, owner: User, vision_id: uuid.UUID
) -> VisionProgress:
    await get_vision(db, owner, vision_id)
    result = await db.execute(
        select(
            func.count(Task.id),
            func.coalesce(func.sum(case((Task.status == TaskStatus.DONE.value, 1), else_=0)), 0),
            func.max(Task.updated_at),
        ).where(
            Task.owner_id == owner.id,
            Task.vision_id == vision_id,
            Task.deleted_at.is_(None),
        )
    )
    total_tasks, done_tasks, last_activity_at = result.one()
    stagnation_days: int | None = None
    if last_activity_at is not None:
        if last_activity_at.tzinfo is None:
            last_activity_at = last_activity_at.replace(tzinfo=UTC)
        stagnation_days = max(0, (datetime.now(UTC) - last_activity_at).days)
    return VisionProgress(
        vision_id=vision_id,
        total_tasks=int(total_tasks or 0),
        done_tasks=int(done_tasks or 0),
        last_activity_at=last_activity_at,
        stagnation_days=stagnation_days,
    )


async def list_stagnating_visions(
    db: AsyncSession, owner: User, days: int
) -> list[StagnatingVision]:
    visions = await list_visions(db, owner)
    items: list[StagnatingVision] = []
    for vision in visions:
        progress = await get_vision_progress(db, owner, vision.id)
        if progress.last_activity_at is not None and (progress.stagnation_days or 0) >= days:
            items.append(
                StagnatingVision(vision=VisionRead.model_validate(vision), progress=progress)
            )
    items.sort(key=lambda item: item.progress.stagnation_days or 0, reverse=True)
    return items


async def get_delete_impact(
    db: AsyncSession, owner: User, vision_id: uuid.UUID
) -> VisionDeleteImpact:
    await get_vision(db, owner, vision_id)
    child_count = (
        await db.execute(
            select(func.count()).where(
                Vision.owner_id == owner.id,
                Vision.parent_id == vision_id,
                Vision.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    task_count = (
        await db.execute(
            select(func.count()).where(
                Task.owner_id == owner.id,
                Task.vision_id == vision_id,
                Task.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    return VisionDeleteImpact(child_count=child_count, task_count=task_count)


def _collect_descendant_ids(
    vision_id: uuid.UUID, children_by_parent: dict[uuid.UUID | None, list[Vision]]
) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for child in children_by_parent.get(vision_id, []):
        ids.append(child.id)
        ids.extend(_collect_descendant_ids(child.id, children_by_parent))
    return ids


async def delete_vision(
    db: AsyncSession, owner: User, vision_id: uuid.UUID, delete_children: bool = False
) -> None:
    vision = await get_vision(db, owner, vision_id)
    now = datetime.now(UTC)
    ids_to_delete = [vision_id]
    if delete_children:
        visions_by_id = await _load_owner_visions(db, owner)
        children_by_parent: dict[uuid.UUID | None, list[Vision]] = {}
        for other in visions_by_id.values():
            children_by_parent.setdefault(other.parent_id, []).append(other)
        ids_to_delete.extend(_collect_descendant_ids(vision_id, children_by_parent))
    else:
        await db.execute(
            update(Vision)
            .where(
                Vision.owner_id == owner.id,
                Vision.parent_id == vision_id,
                Vision.deleted_at.is_(None),
            )
            .values(parent_id=vision.parent_id)
        )

    await db.execute(
        update(Task)
        .where(
            Task.owner_id == owner.id,
            Task.vision_id.in_(ids_to_delete),
            Task.deleted_at.is_(None),
        )
        .values(vision_id=None)
    )
    await db.execute(
        update(Vision)
        .where(Vision.owner_id == owner.id, Vision.id.in_(ids_to_delete))
        .values(deleted_at=now)
    )
    await db.commit()
