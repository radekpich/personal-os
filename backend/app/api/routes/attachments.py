import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.attachment import (
    AttachmentList,
    AttachmentRead,
    AttachmentUpdate,
    StorageUsage,
    TaskAttachmentCreate,
    TaskAttachmentRead,
)
from app.services import attachment_service

router = APIRouter(prefix="/attachments", tags=["attachments"])
storage_router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
    background_tasks: BackgroundTasks,
    _csrf: Annotated[None, Depends(verify_csrf)],
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form()] = None,
) -> AttachmentRead:
    attachment, created = await attachment_service.upload_attachment(
        db, current_user, settings, file, caption
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    else:
        background_tasks.add_task(
            attachment_service.process_attachment_in_session, db, attachment.id
        )
    return AttachmentRead.model_validate(attachment)


@router.get("/{attachment_id}")
async def get_attachment_file(
    attachment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    attachment = await attachment_service.get_owned_attachment(db, current_user, attachment_id)
    return FileResponse(
        attachment.storage_path,
        media_type=attachment.mime_type,
        filename=attachment.original_filename,
    )


@router.get("/{attachment_id}/thumb")
async def get_attachment_thumbnail(
    attachment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    attachment = await attachment_service.get_owned_attachment(db, current_user, attachment_id)
    if attachment.thumbnail_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="thumbnail not found")
    return FileResponse(attachment.thumbnail_path, media_type="image/jpeg")


@router.patch(
    "/{attachment_id}", response_model=AttachmentRead, dependencies=[Depends(verify_csrf)]
)
async def update_attachment(
    attachment_id: uuid.UUID,
    payload: AttachmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AttachmentRead:
    attachment = await attachment_service.update_attachment_caption(
        db, current_user, attachment_id, payload.caption
    )
    return AttachmentRead.model_validate(attachment)


@router.delete(
    "/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)]
)
async def delete_attachment(
    attachment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await attachment_service.soft_delete_attachment(db, current_user, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


task_router = APIRouter(prefix="/tasks", tags=["tasks"])


@task_router.get("/{task_id}/attachments", response_model=AttachmentList)
async def list_task_attachments(
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AttachmentList:
    attachments = await attachment_service.list_task_attachments(db, current_user, task_id)
    return AttachmentList(items=[AttachmentRead.model_validate(item) for item in attachments])


@task_router.post(
    "/{task_id}/attachments",
    response_model=TaskAttachmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def attach_task_attachment(
    task_id: uuid.UUID,
    payload: TaskAttachmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskAttachmentRead:
    link = await attachment_service.attach_to_task(
        db, current_user, task_id, payload.attachment_id, payload.position
    )
    return TaskAttachmentRead(
        task_id=link.task_id, attachment_id=link.attachment_id, position=link.position
    )


@task_router.delete(
    "/{task_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def detach_task_attachment(
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await attachment_service.detach_from_task(db, current_user, task_id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@storage_router.get("/usage", response_model=StorageUsage)
async def get_storage_usage(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StorageUsage:
    (
        file_count,
        used_bytes,
        max_bytes,
        remaining_bytes,
        used_percent,
    ) = await attachment_service.storage_usage(db, current_user, settings)
    return StorageUsage(
        file_count=file_count,
        used_bytes=used_bytes,
        max_bytes=max_bytes,
        remaining_bytes=remaining_bytes,
        used_percent=used_percent,
    )
