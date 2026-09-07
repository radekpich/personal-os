from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from httpx import AsyncClient
from pytest import CaptureFixture, MonkeyPatch
from sqlalchemy import select

from app.api.deps import require_api_key_scope
from app.main import app
from app.models.user import User
from app.services.api_key_service import ApiKeyIdentity
from tests.conftest import TestSessionLocal

api_key_read_dependency = Depends(require_api_key_scope("tasks:read"))


async def _test_agent_protected_route(
    identity: Annotated[ApiKeyIdentity, api_key_read_dependency],
) -> dict[str, str]:
    return {"owner_id": str(identity.owner_id), "api_key_id": str(identity.api_key_id)}


if not any(getattr(route, "path", None) == "/__test/agent-protected" for route in app.routes):
    app.add_api_route(
        "/__test/agent-protected",
        _test_agent_protected_route,
        methods=["GET"],
    )


async def test_create_api_key_returns_plaintext_once_and_stores_only_hash(test_user: User) -> None:
    from app.models.api_key import ApiKey
    from app.services.api_key_service import create_api_key, verify_api_key

    async with TestSessionLocal() as session:
        created = await create_api_key(
            session,
            owner_id=test_user.id,
            name="Telegram agent",
            scopes=["tasks:read", "tasks:write"],
        )
        await session.commit()

        assert created.plaintext_key.startswith("pos_")
        assert len(created.plaintext_key) > 40
        assert created.record.key_prefix == created.plaintext_key[:8]
        assert created.record.key_hash != created.plaintext_key
        assert created.record.scopes == ["tasks:read", "tasks:write"]

        stored = (await session.execute(select(ApiKey))).scalar_one()
        assert stored.key_hash == created.record.key_hash
        assert created.plaintext_key not in stored.key_hash

        identity = await verify_api_key(session, created.plaintext_key, required_scope="tasks:read")
        assert identity is not None
        assert identity.owner_id == test_user.id
        assert identity.api_key_id == created.record.id
        assert identity.scopes == ["tasks:read", "tasks:write"]


async def test_x_api_key_dependency_enforces_scope_and_updates_last_used(
    client: AsyncClient, test_user: User
) -> None:
    from app.models.api_key import ApiKey
    from app.services.api_key_service import create_api_key

    async with TestSessionLocal() as session:
        created = await create_api_key(
            session,
            owner_id=test_user.id,
            name="Read only agent",
            scopes=["tasks:read"],
        )
        plaintext = created.plaintext_key
        key_id = created.record.id
        await session.commit()

    response = await client.get("/__test/agent-protected", headers={"X-API-Key": plaintext})
    assert response.status_code == 200
    assert response.json()["owner_id"] == str(test_user.id)
    assert response.json()["api_key_id"] == str(key_id)

    async with TestSessionLocal() as session:
        stored = await session.get(ApiKey, key_id)
        assert stored is not None
        assert stored.last_used_at is not None

    async with TestSessionLocal() as session:
        no_scope = await create_api_key(
            session,
            owner_id=test_user.id,
            name="No scope",
            scopes=["journal:read"],
        )
        await session.commit()
    response = await client.get(
        "/__test/agent-protected", headers={"X-API-Key": no_scope.plaintext_key}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "missing_scope"


async def test_revoked_and_expired_api_keys_are_rejected(test_user: User) -> None:
    from app.services.api_key_service import create_api_key, verify_api_key

    async with TestSessionLocal() as session:
        revoked = await create_api_key(
            session,
            owner_id=test_user.id,
            name="Revoked",
            scopes=["tasks:read"],
        )
        revoked.record.revoked_at = datetime.now(UTC)
        expired = await create_api_key(
            session,
            owner_id=test_user.id,
            name="Expired",
            scopes=["tasks:read"],
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        await session.commit()

        revoked_identity = await verify_api_key(
            session, revoked.plaintext_key, required_scope="tasks:read"
        )
        expired_identity = await verify_api_key(
            session, expired.plaintext_key, required_scope="tasks:read"
        )
        assert revoked_identity is None
        assert expired_identity is None


async def test_cli_create_and_revoke_api_key_prints_plaintext_once(
    test_user: User, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    from app import cli
    from app.models.api_key import ApiKey

    monkeypatch.setattr(cli, "AsyncSessionLocal", TestSessionLocal)

    await cli._create_api_key(
        email=test_user.email,
        name="Telegram agent",
        scopes=["tasks:read", "tasks:write"],
        expires_at=None,
    )
    output = capsys.readouterr().out
    key_line = next(line for line in output.splitlines() if line.startswith("API key: "))
    plaintext = key_line.removeprefix("API key: ").strip()
    assert plaintext.startswith("pos_")

    async with TestSessionLocal() as session:
        stored = (await session.execute(select(ApiKey))).scalar_one()
        assert stored.key_prefix == plaintext[:8]
        assert plaintext not in stored.key_hash
        prefix = stored.key_prefix

    await cli._revoke_api_key(key_id=None, key_prefix=prefix)
    revoke_output = capsys.readouterr().out
    assert "Revoked API key" in revoke_output

    async with TestSessionLocal() as session:
        stored = (await session.execute(select(ApiKey))).scalar_one()
        assert stored.revoked_at is not None
