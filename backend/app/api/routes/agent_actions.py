import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.agent_action import AgentAction, AgentActionType
from app.models.note import Note
from app.models.task import Task
from app.models.user import User
from app.schemas.agent_action import (
    AgentActionList,
    AgentActionRead,
    RevertBatchRequest,
    RevertResult,
)

router = APIRouter(prefix="/agent/actions", tags=["agent-actions"])

_RESTORE_FIELDS = {
    "task": {
        "title",
        "description",
        "status",
        "priority",
        "due_date",
        "due_time",
        "estimate_minutes",
        "completed_at",
        "category_id",
        "context_id",
        "vision_id",
        "parent_task_id",
        "recurrence_template_id",
        "recurrence_rule",
        "recurrence_mode",
        "position",
    },
    "note": {
        "title",
        "body",
        "kind",
        "entry_date",
        "entry_time",
        "mood",
        "category_id",
        "vision_id",
        "task_id",
    },
}


@router.get("", response_model=AgentActionList)
async def list_actions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    action: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query(max_length=40)] = None,
    source_system: Annotated[str | None, Query(max_length=80)] = None,
    entity_type: Annotated[str | None, Query(max_length=40)] = None,
    entity_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: Annotated[datetime | None, Query()] = None,
    only_unreverted: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AgentActionList:
    conditions = [AgentAction.owner_id == current_user.id]
    if action:
        conditions.append(AgentAction.action == action)
    if source:
        conditions.append(AgentAction.source == source)
    if source_system:
        conditions.append(AgentAction.source_system == source_system)
    if entity_type:
        conditions.append(AgentAction.entity_type == entity_type)
    if entity_id:
        conditions.append(AgentAction.entity_id == entity_id)
    if created_from:
        conditions.append(AgentAction.created_at >= created_from)
    if created_to:
        conditions.append(AgentAction.created_at <= created_to)
    if only_unreverted:
        conditions.append(AgentAction.reverted_at.is_(None))
    total = (
        await db.execute(select(func.count()).select_from(AgentAction).where(*conditions))
    ).scalar_one()
    rows = (
        (
            await db.execute(
                select(AgentAction)
                .where(*conditions)
                .order_by(AgentAction.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return AgentActionList(
        items=[AgentActionRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def _load_entity(db: AsyncSession, action: AgentAction) -> Task | Note | None:
    if action.entity_id is None:
        return None
    if action.entity_type == "task":
        return await db.get(Task, action.entity_id)
    if action.entity_type == "note":
        return await db.get(Note, action.entity_id)
    return None


def _current_snapshot(entity: Task | Note) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in _RESTORE_FIELDS["task" if isinstance(entity, Task) else "note"] | {
        "version",
        "updated_by",
        "deleted_at",
    }:
        value = getattr(entity, field)
        if isinstance(value, datetime) or hasattr(value, "isoformat"):
            data[field] = value.isoformat()
        elif value is None or isinstance(value, str | int | float | bool):
            data[field] = value
        else:
            data[field] = str(value)
    return data


def _conflict(action: AgentAction, entity: Task | Note) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "revert_conflict",
            "message": "Record changed after agent action; review diff before reverting",
            "action_id": str(action.id),
            "entity_type": action.entity_type,
            "entity_id": str(action.entity_id),
            "before_json": action.before_json,
            "result_json": action.result_json,
            "current_state": _current_snapshot(entity),
        },
    )


def _ensure_safe_revert(action: AgentAction, entity: Task | Note) -> None:
    result_version = None
    if isinstance(action.result_json, dict):
        raw = action.result_json.get("version")
        if isinstance(raw, int):
            result_version = raw
    if (
        entity.updated_by == "user"
        and result_version is not None
        and entity.version != result_version
    ):
        _conflict(action, entity)


def _apply_before(action: AgentAction, entity: Task | Note) -> None:
    if action.action in {AgentActionType.CREATE_TASK.value, AgentActionType.ADD_NOTE.value}:
        entity.deleted_at = datetime.now(UTC)
    elif action.before_json:
        for field in _RESTORE_FIELDS[action.entity_type]:
            if field in action.before_json:
                setattr(entity, field, action.before_json[field])
        entity.deleted_at = None
    if hasattr(entity, "version"):
        entity.version += 1
        entity.updated_by = "user"
        entity.api_key_id = None


async def _revert_one(db: AsyncSession, current_user: User, action: AgentAction) -> uuid.UUID:
    if action.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="action not found")
    if action.reverted_at is not None:
        return action.id
    entity = await _load_entity(db, action)
    if entity is None or entity.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entity not found")
    _ensure_safe_revert(action, entity)
    _apply_before(action, entity)
    action.reverted_at = datetime.now(UTC)
    db.add(entity)
    db.add(action)
    db.add(
        AgentAction(
            owner_id=current_user.id,
            api_key_id=None,
            action=AgentActionType.REVERT_ACTION.value,
            entity_type=action.entity_type,
            entity_id=action.entity_id,
            payload_json={"reverted_action_id": str(action.id)},
            before_json=_current_snapshot(entity),
            result_json={"reverted_action_id": str(action.id)},
            reasoning="User reverted agent action from Activity screen",
            source="manual",
            batch_id=action.batch_id,
        )
    )
    return action.id


@router.post(
    "/{action_id}/revert", response_model=RevertResult, dependencies=[Depends(verify_csrf)]
)
async def revert_action(
    action_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RevertResult:
    action = await db.get(AgentAction, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="action not found")
    reverted_id = await _revert_one(db, current_user, action)
    await db.commit()
    return RevertResult(reverted_action_ids=[reverted_id])


@router.post("/revert-batch", response_model=RevertResult, dependencies=[Depends(verify_csrf)])
async def revert_batch(
    payload: RevertBatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RevertResult:
    if payload.batch_id is None and payload.created_from is None and payload.created_to is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="batch_id or time window required"
        )
    conditions = [AgentAction.owner_id == current_user.id, AgentAction.reverted_at.is_(None)]
    if payload.batch_id is not None:
        conditions.append(AgentAction.batch_id == payload.batch_id)
    if payload.created_from is not None:
        conditions.append(AgentAction.created_at >= payload.created_from)
    if payload.created_to is not None:
        conditions.append(AgentAction.created_at <= payload.created_to)
    actions = (
        (
            await db.execute(
                select(AgentAction).where(*conditions).order_by(AgentAction.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    reverted = [await _revert_one(db, current_user, action) for action in actions]
    db.add(
        AgentAction(
            owner_id=current_user.id,
            api_key_id=None,
            action=AgentActionType.REVERT_BATCH.value,
            entity_type="batch",
            entity_id=None,
            payload_json=payload.model_dump(mode="json"),
            before_json=None,
            result_json={"reverted_action_ids": [str(item) for item in reverted]},
            reasoning="User reverted agent action batch from Activity screen",
            source="manual",
            batch_id=payload.batch_id,
        )
    )
    await db.commit()
    return RevertResult(reverted_action_ids=reverted)
