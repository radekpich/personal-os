import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User

settings = get_settings()


class AuthenticationError(Exception):
    pass


class TokenReuseError(Exception):
    pass


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise AuthenticationError("invalid credentials")
    return user


async def issue_tokens(
    db: AsyncSession, user: User, family_id: uuid.UUID | None = None
) -> tuple[str, str]:
    now = datetime.now(UTC)
    access_token = create_access_token(user.id)
    refresh_token = generate_refresh_token()
    token_row = RefreshToken(
        user_id=user.id,
        family_id=family_id or uuid.uuid4(),
        token_hash=hash_refresh_token(refresh_token),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(token_row)
    await db.commit()
    return access_token, refresh_token


async def rotate_refresh_token(db: AsyncSession, presented_token: str) -> tuple[str, str, User]:
    token_hash = hash_refresh_token(presented_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_row = result.scalar_one_or_none()
    if token_row is None:
        raise AuthenticationError("invalid refresh token")

    now = datetime.now(UTC)

    if token_row.revoked_at is not None:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == token_row.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await db.commit()
        raise TokenReuseError("refresh token reuse detected")

    if _aware(token_row.expires_at) < now:
        raise AuthenticationError("refresh token expired")

    user_result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AuthenticationError("user not found")

    token_row.revoked_at = now
    db.add(token_row)

    access_token, new_refresh_token = await issue_tokens(db, user, family_id=token_row.family_id)
    return access_token, new_refresh_token, user


async def revoke_refresh_token(db: AsyncSession, presented_token: str) -> None:
    token_hash = hash_refresh_token(presented_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_row = result.scalar_one_or_none()
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(UTC)
        db.add(token_row)
        await db.commit()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
