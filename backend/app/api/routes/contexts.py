import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.context import Context
from app.models.user import User
from app.schemas.context import ContextCreate, ContextList, ContextRead, ContextUpdate
from app.services import context_service

router = APIRouter(prefix="/contexts", tags=["contexts"])


@router.get("", response_model=ContextList)
async def list_contexts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ContextList:
    return ContextList(items=await context_service.list_contexts(db, current_user))


@router.post(
    "",
    response_model=ContextRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_context(
    payload: ContextCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Context:
    return await context_service.create_context(db, current_user, payload)


@router.patch("/{context_id}", response_model=ContextRead, dependencies=[Depends(verify_csrf)])
async def update_context(
    context_id: uuid.UUID,
    payload: ContextUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Context:
    return await context_service.update_context(db, current_user, context_id, payload)


@router.delete(
    "/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_context(
    context_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await context_service.delete_context(db, current_user, context_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
