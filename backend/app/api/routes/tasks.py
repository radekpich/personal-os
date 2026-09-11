import uuid
from datetime import date, datetime, time
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ActorContext, get_current_actor, verify_csrf_or_api_key
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.task import Task, TaskSource, TaskStatus
from app.schemas.task import TaskCreate, TaskList, TaskRead, TaskUpdate, TaskView
from app.services import task_service
from app.services.concurrency import ConflictError
from app.services.task_service import TaskListFilters

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _require_if_match(if_match: int | None) -> int:
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "if_match_required",
                "message": "If-Match header with expected version is required",
                "field": "If-Match",
            },
        )
    return if_match


def _raise_conflict(exc: ConflictError) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": exc.code,
            "message": exc.message,
            "field": "If-Match" if exc.code == "version_conflict" else None,
            "current_state": exc.current_state,
        },
    ) from exc


@router.get("", response_model=TaskList)
async def list_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    context_id: Annotated[uuid.UUID | None, Query()] = None,
    tag_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    due_from: Annotated[date | None, Query()] = None,
    due_to: Annotated[date | None, Query()] = None,
    created_from: Annotated[date | None, Query()] = None,
    created_to: Annotated[date | None, Query()] = None,
    source: Annotated[TaskSource | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    view: Annotated[TaskView | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TaskList:
    filters = TaskListFilters(
        status=status_filter,
        category_id=category_id,
        context_id=context_id,
        tag_ids=tag_ids,
        due_from=due_from,
        due_to=due_to,
        created_from=datetime.combine(created_from, time.min) if created_from is not None else None,
        created_to=datetime.combine(created_to, time.max) if created_to is not None else None,
        source=source,
        q=q,
        view=view,
        page=page,
        page_size=page_size,
    )
    tasks, total = await task_service.list_tasks(db, actor_context.user, filters)
    return TaskList(
        items=[TaskRead.model_validate(task) for task in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/quick",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def quick_create_task(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> Task:
    body = await request.body()
    title = body.decode("utf-8")
    return await task_service.quick_create_task(
        db,
        actor_context.user,
        title,
        actor=actor_context.actor,
        api_key_id=actor_context.api_key_id,
    )


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def create_task(
    payload: TaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> Task:
    return await task_service.create_task(
        db,
        actor_context.user,
        payload,
        actor=actor_context.actor,
        api_key_id=actor_context.api_key_id,
    )


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> Task:
    return await task_service.get_task(db, actor_context.user, task_id)


@router.patch("/{task_id}", response_model=TaskRead, dependencies=[Depends(verify_csrf_or_api_key)])
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    if_match: Annotated[int | None, Header(alias="If-Match")] = None,
) -> Task:
    try:
        return await task_service.update_task(
            db,
            actor_context.user,
            task_id,
            payload,
            expected_version=_require_if_match(if_match),
            fresh_user_edit_guard_minutes=settings.fresh_user_edit_guard_minutes,
            actor=actor_context.actor,
            api_key_id=actor_context.api_key_id,
        )
    except ConflictError as exc:
        _raise_conflict(exc)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def delete_task(
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    if_match: Annotated[int | None, Header(alias="If-Match")] = None,
) -> Response:
    try:
        await task_service.delete_task(
            db,
            actor_context.user,
            task_id,
            expected_version=_require_if_match(if_match),
            fresh_user_edit_guard_minutes=settings.fresh_user_edit_guard_minutes,
            actor=actor_context.actor,
            api_key_id=actor_context.api_key_id,
        )
    except ConflictError as exc:
        _raise_conflict(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
