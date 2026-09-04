from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, StatusResponse
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()


def _set_auth_cookies(
    response: Response, settings: Settings, access_token: str, refresh_token: str
) -> None:
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.access_cookie_name, path="/")
    response.delete_cookie(settings.refresh_cookie_name, path="/")


@router.post(
    "/login",
    response_model=UserRead,
    dependencies=[Depends(verify_csrf)],
)
@limiter.limit(_settings.rate_limit_login)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    try:
        user = await auth_service.authenticate_user(db, payload.email, payload.password)
    except auth_service.AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
        ) from exc
    access_token, refresh_token = await auth_service.issue_tokens(db, user)
    _set_auth_cookies(response, settings, access_token, refresh_token)
    return user


@router.post("/refresh", response_model=StatusResponse, dependencies=[Depends(verify_csrf)])
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatusResponse:
    presented_token = request.cookies.get(settings.refresh_cookie_name)
    if presented_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing refresh token"
        )
    try:
        access_token, new_refresh_token, _user = await auth_service.rotate_refresh_token(
            db, presented_token
        )
    except auth_service.TokenReuseError as exc:
        _clear_auth_cookies(response, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token reuse detected"
        ) from exc
    except auth_service.AuthenticationError as exc:
        _clear_auth_cookies(response, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        ) from exc
    _set_auth_cookies(response, settings, access_token, new_refresh_token)
    return StatusResponse(status="ok")


@router.post("/logout", response_model=StatusResponse, dependencies=[Depends(verify_csrf)])
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatusResponse:
    presented_token = request.cookies.get(settings.refresh_cookie_name)
    if presented_token is not None:
        await auth_service.revoke_refresh_token(db, presented_token)
    _clear_auth_cookies(response, settings)
    return StatusResponse(status="ok")


@router.get("/me", response_model=UserRead)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
