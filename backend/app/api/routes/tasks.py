import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskList, TaskRead, TaskUpdate, TaskView
from app.services import task_service
from app.services.task_service import TaskListFilters

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskList)
async def list_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    context_id: Annotated[uuid.UUID | None, Query()] = None,
    tag_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    due_from: Annotated[date | None, Query()] = None,
    due_to: Annotated[date | None, Query()] = None,
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
        q=q,
        view=view,
        page=page,
        page_size=page_size,
    )
    tasks, total = await task_service.list_tasks(db, current_user, filters)
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
    dependencies=[Depends(verify_csrf)],
)
async def quick_create_task(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Task:
    body = await request.body()
    title = body.decode("utf-8")
    return await task_service.quick_create_task(db, current_user, title)


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_task(
    payload: TaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Task:
    return await task_service.create_task(db, current_user, payload)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Task:
    return await task_service.get_task(db, current_user, task_id)


@router.patch("/{task_id}", response_model=TaskRead, dependencies=[Depends(verify_csrf)])
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Task:
    return await task_service.update_task(db, current_user, task_id, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_task(
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await task_service.delete_task(db, current_user, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
