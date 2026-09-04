from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    token = request.cookies.get(settings.access_cookie_name)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        ) from exc
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user


async def verify_csrf(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get(settings.csrf_header_name)
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
