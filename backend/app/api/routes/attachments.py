import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.attachment import AttachmentRead, StorageUsage
from app.services import attachment_service

router = APIRouter(prefix="/attachments", tags=["attachments"])
storage_router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
    _csrf: Annotated[None, Depends(verify_csrf)],
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form()] = None,
) -> AttachmentRead:
    attachment, created = await attachment_service.upload_attachment(
        db, current_user, settings, file, caption
    )
    if not created:
        response.status_code = status.HTTP_200_OK
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
