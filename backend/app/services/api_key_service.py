import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey

API_KEY_PREFIX = "pos_"


@dataclass(frozen=True)
class CreatedApiKey:
    record: ApiKey
    plaintext_key: str


@dataclass(frozen=True)
class ApiKeyIdentity:
    owner_id: uuid.UUID
    api_key_id: uuid.UUID
    scopes: list[str]


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _is_expired(expires_at: datetime | None, now: datetime) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now


async def create_api_key(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
) -> CreatedApiKey:
    plaintext_key = generate_api_key()
    record = ApiKey(
        owner_id=owner_id,
        name=name,
        key_hash=hash_api_key(plaintext_key),
        key_prefix=plaintext_key[:8],
        scopes=scopes,
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return CreatedApiKey(record=record, plaintext_key=plaintext_key)


async def verify_api_key(
    db: AsyncSession, plaintext_key: str, *, required_scope: str | None = None
) -> ApiKeyIdentity | None:
    if not plaintext_key:
        return None
    key_hash = hash_api_key(plaintext_key)
    record = (
        await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if record is None or record.revoked_at is not None or _is_expired(record.expires_at, now):
        return None
    scopes = list(record.scopes)
    if required_scope is not None and required_scope not in scopes:
        return None
    record.last_used_at = now
    await db.flush()
    return ApiKeyIdentity(owner_id=record.owner_id, api_key_id=record.id, scopes=scopes)


async def revoke_api_key(
    db: AsyncSession, *, key_id: uuid.UUID | None = None, key_prefix: str | None = None
) -> ApiKey | None:
    if key_id is None and key_prefix is None:
        raise ValueError("key_id or key_prefix is required")
    stmt = select(ApiKey)
    if key_id is not None:
        stmt = stmt.where(ApiKey.id == key_id)
    else:
        stmt = stmt.where(ApiKey.key_prefix == key_prefix)
    record = (await db.execute(stmt)).scalar_one_or_none()
    if record is None:
        return None
    record.revoked_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(record)
    return record
