import uuid
from datetime import date
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.note import Note, NoteKind
from app.models.user import User
from app.schemas.attachment import (
    AttachmentList,
    AttachmentRead,
    NoteAttachmentCreate,
    NoteAttachmentRead,
)
from app.schemas.note import NoteCreate, NoteList, NoteRead, NoteUpdate
from app.services import attachment_service, note_service
from app.services.concurrency import ConflictError
from app.services.note_service import NoteListFilters

router = APIRouter(prefix="/notes", tags=["notes"])


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


@router.get("", response_model=NoteList)
async def list_notes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    kind: Annotated[NoteKind | None, Query()] = None,
    entry_date: Annotated[date | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    vision_id: Annotated[uuid.UUID | None, Query()] = None,
    task_id: Annotated[uuid.UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> NoteList:
    filters = NoteListFilters(
        kind=kind,
        entry_date=entry_date,
        date_from=date_from,
        date_to=date_to,
        q=q,
        category_id=category_id,
        vision_id=vision_id,
        task_id=task_id,
        page=page,
        page_size=page_size,
    )
    notes, total = await note_service.list_notes(db, current_user, filters)
    return NoteList(
        items=[NoteRead.model_validate(note) for note in notes],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_note(
    payload: NoteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Note:
    return await note_service.create_note(db, current_user, payload)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Note:
    return await note_service.get_note(db, current_user, note_id)


@router.patch("/{note_id}", response_model=NoteRead, dependencies=[Depends(verify_csrf)])
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    if_match: Annotated[int | None, Header(alias="If-Match")] = None,
) -> Note:
    try:
        return await note_service.update_note(
            db,
            current_user,
            note_id,
            payload,
            expected_version=_require_if_match(if_match),
            fresh_user_edit_guard_minutes=settings.fresh_user_edit_guard_minutes,
        )
    except ConflictError as exc:
        _raise_conflict(exc)


@router.get("/{note_id}/attachments", response_model=AttachmentList)
async def list_note_attachments(
    note_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AttachmentList:
    attachments = await attachment_service.list_note_attachments(db, current_user, note_id)
    return AttachmentList(items=[AttachmentRead.model_validate(item) for item in attachments])


@router.post(
    "/{note_id}/attachments",
    response_model=NoteAttachmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def attach_note_attachment(
    note_id: uuid.UUID,
    payload: NoteAttachmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NoteAttachmentRead:
    link = await attachment_service.attach_to_note(
        db, current_user, note_id, payload.attachment_id, payload.position
    )
    return NoteAttachmentRead(
        note_id=link.note_id, attachment_id=link.attachment_id, position=link.position
    )


@router.delete(
    "/{note_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def detach_note_attachment(
    note_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await attachment_service.detach_from_note(db, current_user, note_id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_note(
    note_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    if_match: Annotated[int | None, Header(alias="If-Match")] = None,
) -> Response:
    try:
        await note_service.delete_note(
            db,
            current_user,
            note_id,
            expected_version=_require_if_match(if_match),
            fresh_user_edit_guard_minutes=settings.fresh_user_edit_guard_minutes,
        )
    except ConflictError as exc:
        _raise_conflict(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
