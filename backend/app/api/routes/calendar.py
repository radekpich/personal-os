from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.security import generate_calendar_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead
from app.services import calendar_ics_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/{token}.ics")
async def get_calendar_feed(token: str, db: Annotated[AsyncSession, Depends(get_db)]) -> Response:
    user = await calendar_ics_service.get_user_by_calendar_token(db, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="calendar not found")
    body = await calendar_ics_service.render_calendar_for_user(db, user)
    return Response(
        content=body,
        headers={
            "Content-Type": "text/calendar; charset=utf-8",
            "Cache-Control": "no-store, max-age=0",
        },
    )


@router.post(
    "/regenerate-token",
    response_model=UserRead,
    dependencies=[Depends(verify_csrf)],
)
async def regenerate_calendar_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    current_user.calendar_token = generate_calendar_token()
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user
