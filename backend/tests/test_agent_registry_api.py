from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.models.agent_registry import AgentConfigChange, AgentIntegration, AgentJob
from app.models.user import User
from app.services.api_key_service import create_api_key
from tests.conftest import CsrfHeaders, TestSessionLocal


async def _report_key(user: User) -> str:
    async with TestSessionLocal() as session:
        created = await create_api_key(
            session,
            owner_id=user.id,
            name="Hermes reporter",
            scopes=["agent:report"],
        )
        await session.commit()
        return created.plaintext_key


def _snapshot(hash_value: str, *, include_drive: bool = False) -> dict[str, object]:
    now = datetime.now(UTC)
    integrations: list[dict[str, object]] = [
        {
            "name": "Telegram Home",
            "kind": "messaging",
            "scopes": ["read", "write"],
            "status": "active",
            "last_used_at": now.isoformat(),
            "error_count": 0,
            "notes": "Home channel only; no token stored",
        }
    ]
    if include_drive:
        integrations.append(
            {
                "name": "Google Drive",
                "kind": "storage",
                "scopes": ["drive.readonly"],
                "status": "active",
                "error_count": 0,
            }
        )
    return {
        "agent": {
            "name": "hermes",
            "version": "2.0.0",
            "host": "ranch-vps",
            "started_at": (now - timedelta(minutes=5)).isoformat(),
        },
        "jobs": [
            {
                "name": "Daily briefing",
                "description": "Morning operational summary",
                "schedule": "0 7 * * *",
                "schedule_description": "každý den v 7:00",
                "is_enabled": True,
                "next_run_at": (now + timedelta(hours=12)).isoformat(),
                "last_status": "success",
                "last_duration_ms": 900,
                "consecutive_failures": 0,
                "run_count": 10,
                "tags": ["briefing"],
            }
        ],
        "integrations": integrations,
        "watches": [
            {
                "name": "Disk",
                "description": "Disk pressure",
                "kind": "system",
                "config_json": {"threshold": 85},
                "schedule": "*/30 * * * *",
                "is_active": True,
            }
        ],
        "channels": [
            {
                "channel_type": "telegram",
                "identifier": "Home",
                "is_active": True,
                "message_count_24h": 3,
                "message_count_month": 44,
            }
        ],
        "capabilities": [
            {
                "name": "web",
                "description": "Web lookup",
                "is_enabled": True,
                "metadata_json": {"toolset": "web"},
            }
        ],
        "snapshot_hash": hash_value,
    }


async def test_registry_sync_requires_agent_report_scope_and_is_idempotent(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    read_only_key = await _report_key(test_user)

    response = await client.post(
        "/agent/registry/sync",
        json=_snapshot("hash-1"),
        headers={"X-API-Key": read_only_key},
    )
    assert response.status_code == 200
    assert response.json()["snapshot_hash"] == "hash-1"
    assert response.json()["changes_created"] == 5

    repeat = await client.post(
        "/agent/registry/sync",
        json=_snapshot("hash-1"),
        headers={"X-API-Key": read_only_key},
    )
    assert repeat.status_code == 200
    assert repeat.json()["idempotent"] is True
    assert repeat.json()["changes_created"] == 0

    async with TestSessionLocal() as session:
        jobs = (await session.execute(select(AgentJob))).scalars().all()
        integrations = (await session.execute(select(AgentIntegration))).scalars().all()
        changes = (await session.execute(select(AgentConfigChange))).scalars().all()
    assert [job.name for job in jobs] == ["Daily briefing"]
    assert [integration.name for integration in integrations] == ["Telegram Home"]
    assert {(change.target_type, change.target_name) for change in changes} == {
        ("job", "Daily briefing"),
        ("integration", "Telegram Home"),
        ("watch", "Disk"),
        ("channel", "telegram:Home"),
        ("capability", "web"),
    }

    changed = await client.post(
        "/agent/registry/sync",
        json=_snapshot("hash-2", include_drive=True),
        headers={"X-API-Key": read_only_key},
    )
    assert changed.status_code == 200
    assert changed.json()["changes_created"] == 1

    async with TestSessionLocal() as session:
        integrations = (await session.execute(select(AgentIntegration))).scalars().all()
        unacknowledged = (
            (
                await session.execute(
                    select(AgentConfigChange).where(AgentConfigChange.acknowledged_at.is_(None))
                )
            )
            .scalars()
            .all()
        )
    assert {integration.name for integration in integrations} == {"Telegram Home", "Google Drive"}
    assert any(change.target_name == "Google Drive" for change in unacknowledged)

    headers = await csrf_headers(client)
    login = await client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-password"},
        headers=headers,
    )
    assert login.status_code == 200
    overview = await client.get("/agent/overview")
    assert overview.status_code == 200
    assert overview.json()["agent"]["status"] == "running"
    assert overview.json()["unacknowledged_change_count"] == 6
    assert overview.json()["active_job_count"] == 1
    assert overview.json()["active_integration_count"] == 2
