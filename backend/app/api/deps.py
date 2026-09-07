import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.api_key_service import ApiKeyIdentity, verify_api_key
from app.services.auth_service import get_user_by_id
from app.services.concurrency import MutationActor


@dataclass(frozen=True)
class ActorContext:
    user: User
    actor: MutationActor
    api_key_id: uuid.UUID | None = None


def _api_error(code: str, message: str, field: str) -> dict[str, str]:
    return {"code": code, "message": message, "field": field}


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


async def verify_csrf_or_api_key(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    if request.headers.get("X-API-Key"):
        return
    await verify_csrf(request, settings)


async def get_current_api_key(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ApiKeyIdentity:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_api_error("api_key_required", "X-API-Key header is required", "X-API-Key"),
        )
    identity = await verify_api_key(db, x_api_key)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_api_error(
                "invalid_api_key", "API key is invalid, expired, or revoked", "X-API-Key"
            ),
        )
    request.state.api_key_identity = identity
    await db.commit()
    return identity


async def get_current_actor(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ActorContext:
    if x_api_key:
        identity = await verify_api_key(db, x_api_key)
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_api_error(
                    "invalid_api_key", "API key is invalid, expired, or revoked", "X-API-Key"
                ),
            )
        user = await get_user_by_id(db, identity.owner_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
        request.state.api_key_identity = identity
        request.state.actor_context = ActorContext(
            user=user, actor=MutationActor.AGENT, api_key_id=identity.api_key_id
        )
        await db.commit()
        return request.state.actor_context
    user = await get_current_user(request, db, settings)
    request.state.actor_context = ActorContext(user=user, actor=MutationActor.USER, api_key_id=None)
    return request.state.actor_context


def require_api_key_scope(scope: str) -> Callable[..., object]:
    async def _dependency(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> ApiKeyIdentity:
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_api_error("api_key_required", "X-API-Key header is required", "X-API-Key"),
            )
        identity = await verify_api_key(db, x_api_key, required_scope=scope)
        if identity is None:
            any_identity = await verify_api_key(db, x_api_key)
            if any_identity is not None:
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_api_error("missing_scope", f"API key requires scope {scope}", "scopes"),
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_api_error(
                    "invalid_api_key",
                    "API key is invalid, expired, or revoked",
                    "X-API-Key",
                ),
            )
        request.state.api_key_identity = identity
        await db.commit()
        return identity

    return _dependency
