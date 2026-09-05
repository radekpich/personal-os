import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.models.vision import Vision
from app.schemas.vision import (
    StagnatingVisionList,
    VisionCreate,
    VisionList,
    VisionProgress,
    VisionRead,
    VisionTree,
    VisionUpdate,
)
from app.services import vision_service

router = APIRouter(prefix="/visions", tags=["visions"])


@router.get("", response_model=VisionList)
async def list_visions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VisionList:
    visions = await vision_service.list_visions(db, current_user)
    return VisionList(items=[VisionRead.model_validate(vision) for vision in visions])


@router.post(
    "",
    response_model=VisionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_vision(
    payload: VisionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Vision:
    return await vision_service.create_vision(db, current_user, payload)


@router.get("/tree", response_model=VisionTree)
async def get_vision_tree(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VisionTree:
    return VisionTree(items=await vision_service.get_vision_tree(db, current_user))


@router.get("/stagnating", response_model=StagnatingVisionList)
async def list_stagnating_visions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=3650)] = 14,
) -> StagnatingVisionList:
    return StagnatingVisionList(
        items=await vision_service.list_stagnating_visions(db, current_user, days)
    )


@router.get("/{vision_id}/progress", response_model=VisionProgress)
async def get_vision_progress(
    vision_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VisionProgress:
    return await vision_service.get_vision_progress(db, current_user, vision_id)


@router.get("/{vision_id}", response_model=VisionRead)
async def get_vision(
    vision_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Vision:
    return await vision_service.get_vision(db, current_user, vision_id)


@router.patch("/{vision_id}", response_model=VisionRead, dependencies=[Depends(verify_csrf)])
async def update_vision(
    vision_id: uuid.UUID,
    payload: VisionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Vision:
    return await vision_service.update_vision(db, current_user, vision_id, payload)


@router.delete(
    "/{vision_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_vision(
    vision_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await vision_service.delete_vision(db, current_user, vision_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
