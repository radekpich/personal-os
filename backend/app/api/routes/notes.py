import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.note import Note, NoteKind
from app.models.user import User
from app.schemas.note import NoteCreate, NoteList, NoteRead, NoteUpdate
from app.services import note_service
from app.services.note_service import NoteListFilters

router = APIRouter(prefix="/notes", tags=["notes"])


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
) -> Note:
    return await note_service.update_note(db, current_user, note_id, payload)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_note(
    note_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await note_service.delete_note(db, current_user, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
