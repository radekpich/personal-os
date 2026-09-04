import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("invalid token") from exc
    if payload.get("type") != "access":
        raise InvalidTokenError("wrong token type")
    try:
        return uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("invalid subject") from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
