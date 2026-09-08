from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.models.agent_registry import (
    AgentConfigChange,
    AgentJob,
    AgentWatch,
)
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.api_key_service import create_api_key
from tests.conftest import CsrfHeaders, TestSessionLocal


async def _api_key(user: User, scopes: list[str]) -> str:
    async with TestSessionLocal() as session:
        created = await create_api_key(session, owner_id=user.id, name="key", scopes=scopes)
        await session.commit()
        return created.plaintext_key


def _snapshot(hash_value: str) -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "agent": {
            "name": "hermes",
            "version": "2.0.0",
            "host": "ranch-vps",
            "started_at": now.isoformat(),
        },
        "jobs": [
            {
                "name": "Hourly audit",
                "schedule": "0 * * * *",
                "schedule_description": "každou hodinu",
                "is_enabled": True,
                "next_run_at": (now + timedelta(hours=1)).isoformat(),
                "tags": ["audit"],
            }
        ],
        "integrations": [
            {
                "name": "Gmail",
                "kind": "email",
                "scopes": ["gmail.readonly"],
                "status": "active",
                "error_count": 0,
            }
        ],
        "watches": [
            {
                "name": "Disk",
                "kind": "system",
                "config_json": {"threshold": 85},
                "schedule": "*/30 * * * *",
                "is_active": True,
            }
        ],
        "channels": [],
        "capabilities": [],
        "snapshot_hash": hash_value,
    }


async def _seed_registry(client: AsyncClient, user: User) -> str:
    key = await _api_key(user, ["agent:report"])
    response = await client.post(
        "/agent/registry/sync", json=_snapshot("seed"), headers={"X-API-Key": key}
    )
    assert response.status_code == 200
    return key


async def _login(client: AsyncClient, user: User, csrf_headers: CsrfHeaders) -> None:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200


async def test_agent_runs_batch_watch_report_and_history_filters(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    key = await _seed_registry(client, test_user)
    async with TestSessionLocal() as session:
        job = (
            await session.execute(select(AgentJob).where(AgentJob.name == "Hourly audit"))
        ).scalar_one()
        watch = (
            await session.execute(select(AgentWatch).where(AgentWatch.name == "Disk"))
        ).scalar_one()

    started = datetime.now(UTC) - timedelta(seconds=4)
    runs = await client.post(
        "/agent/runs",
        json={
            "runs": [
                {
                    "job_id": str(job.id),
                    "trigger": "schedule",
                    "summary": "Checked disk and security posture.",
                    "detail": "Everything ok.",
                    "status": "success",
                    "started_at": started.isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "duration_ms": 4000,
                    "tokens_used": 120,
                    "cost_estimate": 0.02,
                    "tags": ["audit"],
                },
                {
                    "trigger": "telegram",
                    "summary": "Answered a family calendar question.",
                    "status": "success",
                    "started_at": datetime.now(UTC).isoformat(),
                    "tags": ["calendar"],
                },
            ]
        },
        headers={"X-API-Key": key},
    )
    assert runs.status_code == 200
    assert runs.json()["created"] == 2

    watch_report = await client.post(
        f"/agent/watches/{watch.id}/report",
        json={"checked_at": datetime.now(UTC).isoformat(), "triggered": True, "result": "disk 82%"},
        headers={"X-API-Key": key},
    )
    assert watch_report.status_code == 200

    await _login(client, test_user, csrf_headers)
    history = await client.get("/agent/runs?trigger=schedule&q=disk&page_size=10")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["summary"] == "Checked disk and security posture."

    async with TestSessionLocal() as session:
        updated_watch = await session.get(AgentWatch, watch.id)
        assert updated_watch is not None
        assert updated_watch.trigger_count == 1
        assert updated_watch.last_result == "disk 82%"


async def test_agent_registry_read_lists_acknowledge_and_revoke_all(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    report_key = await _seed_registry(client, test_user)
    await _api_key(test_user, ["tasks:read", "tasks:write"])
    await _login(client, test_user, csrf_headers)

    jobs = await client.get("/agent/jobs")
    integrations = await client.get("/agent/integrations")
    watches = await client.get("/agent/watches")
    changes = await client.get("/agent/config-changes?acknowledged=false")
    keys = await client.get("/agent/keys")
    assert (
        jobs.status_code
        == integrations.status_code
        == watches.status_code
        == changes.status_code
        == keys.status_code
        == 200
    )
    assert jobs.json()["items"][0]["name"] == "Hourly audit"
    assert integrations.json()["items"][0]["scopes"] == ["gmail.readonly"]
    assert watches.json()["items"][0]["name"] == "Disk"
    assert changes.json()["total"] >= 3
    assert any("agent:report" in item["scopes"] for item in keys.json()["items"])

    async with TestSessionLocal() as session:
        change = (await session.execute(select(AgentConfigChange))).scalars().first()
        assert change is not None
    headers = await csrf_headers(client)
    ack = await client.post(f"/agent/config-changes/{change.id}/acknowledge", headers=headers)
    assert ack.status_code == 200

    headers = await csrf_headers(client)
    revoke = await client.post("/agent/keys/revoke-all", headers=headers)
    assert revoke.status_code == 200
    assert revoke.json()["revoked_count"] >= 2

    response = await client.post(
        "/agent/runs", json={"runs": []}, headers={"X-API-Key": report_key}
    )
    assert response.status_code == 401
    async with TestSessionLocal() as session:
        keys_after = (await session.execute(select(ApiKey))).scalars().all()
    assert all(key.revoked_at is not None for key in keys_after)
