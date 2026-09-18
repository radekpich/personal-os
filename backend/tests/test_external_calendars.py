from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from httpx import AsyncClient

from app.models.external_calendar import CalendarRequest, CalendarRequestStatus
from app.models.task import Task
from app.models.user import User
from app.services.api_key_service import create_api_key
from app.services.external_calendar_service import release_stale_claims
from tests.conftest import CsrfHeaders, TestSessionLocal


async def _api_key(test_user: User, scopes: list[str]) -> str:
    async with TestSessionLocal() as session:
        created = await create_api_key(
            session,
            owner_id=test_user.id,
            name="Calendar agent",
            scopes=scopes,
        )
        await session.commit()
        return created.plaintext_key


async def _login(
    client: AsyncClient, csrf_headers: CsrfHeaders, email: str, password: str
) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login", json={"email": email, "password": password}, headers=headers
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def _create_task(
    client: AsyncClient, csrf: dict[str, str], title: str = "Calendar task"
) -> dict[str, Any]:
    response = await client.post(
        "/tasks",
        json={"title": title, "due_date": "2026-10-02", "due_time": "14:30"},
        headers=csrf,
    )
    assert response.status_code == 201
    return dict(response.json())


async def test_agent_sync_calendars_replaces_list_and_hides_readonly(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    key = await _api_key(test_user, ["calendar:report"])
    response = await client.post(
        "/agent/calendars/sync",
        headers={"X-API-Key": key},
        json={
            "calendars": [
                {
                    "external_id": "primary",
                    "name": "Radek",
                    "color": "#4285f4",
                    "can_write": True,
                    "is_shared": False,
                    "is_primary": True,
                    "is_enabled": True,
                    "is_default": True,
                },
                {
                    "external_id": "readonly",
                    "name": "Read only",
                    "can_write": False,
                    "is_shared": True,
                    "is_primary": False,
                    "is_enabled": True,
                    "is_default": False,
                },
            ]
        },
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["external_id"] for item in items} == {"primary", "readonly"}
    assert next(item for item in items if item["external_id"] == "readonly")["is_enabled"] is False
    assert all(item["last_synced_at"] for item in items)

    # Replacement semantics: missing calendars disappear.
    second = await client.post(
        "/agent/calendars/sync",
        headers={"X-API-Key": key},
        json={
            "calendars": [
                {
                    "external_id": "family",
                    "name": "KataPick",
                    "color": "#00aa55",
                    "can_write": True,
                    "is_shared": True,
                    "is_primary": False,
                    "is_enabled": True,
                    "is_default": True,
                }
            ]
        },
    )
    assert second.status_code == 200
    assert [item["external_id"] for item in second.json()["items"]] == ["family"]

    csrf = await _login(client, csrf_headers, test_user.email, "correct-password")
    listed = await client.get("/external-calendars", headers=csrf)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["is_shared"] is True


async def test_calendar_request_is_idempotent_claimed_atomically_and_completed(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    report_key = await _api_key(test_user, ["calendar:report"])
    write_key = await _api_key(test_user, ["calendar:write"])
    await client.post(
        "/agent/calendars/sync",
        headers={"X-API-Key": report_key},
        json={
            "calendars": [
                {
                    "external_id": "family",
                    "name": "KataPick",
                    "can_write": True,
                    "is_shared": True,
                    "is_primary": False,
                    "is_enabled": True,
                    "is_default": True,
                }
            ]
        },
    )
    csrf = await _login(client, csrf_headers, test_user.email, "correct-password")
    task = await _create_task(client, csrf)
    payload = {
        "calendar_external_id": "family",
        "starts_at": "2026-10-02T14:30:00+02:00",
        "ends_at": "2026-10-02T15:00:00+02:00",
        "reminder_minutes": 15,
        "idempotency_key": "task-family-1",
    }
    first = await client.post(f"/tasks/{task['id']}/calendar-request", json=payload, headers=csrf)
    second = await client.post(f"/tasks/{task['id']}/calendar-request", json=payload, headers=csrf)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    request_id = first.json()["id"]

    pending = await client.get(
        "/agent/calendar-requests?status=pending", headers={"X-API-Key": write_key}
    )
    assert pending.status_code == 200
    assert [item["id"] for item in pending.json()["items"]] == [request_id]

    claimed = await client.post(
        f"/agent/calendar-requests/{request_id}/claim", headers={"X-API-Key": write_key}
    )
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "claimed"
    duplicate_claim = await client.post(
        f"/agent/calendar-requests/{request_id}/claim", headers={"X-API-Key": write_key}
    )
    assert duplicate_claim.status_code == 409

    completed = await client.post(
        f"/agent/calendar-requests/{request_id}/complete",
        headers={"X-API-Key": write_key},
        json={
            "external_event_id": "google-123",
            "external_event_link": "https://calendar.google.com/event?eid=123",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"
    assert completed.json()["external_event_link"].startswith("https://calendar.google.com")


async def test_stale_claims_are_released_and_fail_after_three_attempts(test_user: User) -> None:
    now = datetime.now(UTC)
    async with TestSessionLocal() as session:
        task = Task(owner_id=test_user.id, title="Stale calendar request")
        session.add(task)
        await session.flush()
        request = CalendarRequest(
            owner_id=test_user.id,
            task_id=task.id,
            operation="create",
            calendar_external_id="family",
            title="Stale calendar request",
            starts_at=now,
            ends_at=now + timedelta(minutes=30),
            status=CalendarRequestStatus.CLAIMED.value,
            claimed_at=now - timedelta(minutes=6),
            attempt_count=2,
            idempotency_key="stale-1",
        )
        session.add_all([task, request])
        await session.commit()
        request_id = request.id

    result = await release_stale_claims(TestSessionLocal)
    assert result == {"released": 0, "failed": 1}
    async with TestSessionLocal() as session:
        stored = await session.get(CalendarRequest, request_id)
        assert stored is not None
        assert stored.status == CalendarRequestStatus.FAILED.value
        assert stored.attempt_count == 3


async def test_ics_feed_skips_tasks_with_real_calendar_request(
    client: AsyncClient, test_user: User
) -> None:
    now = datetime.now(UTC)
    async with TestSessionLocal() as session:
        task_plain = Task(
            owner_id=test_user.id,
            title="Plain feed task",
            due_date=date(2026, 10, 5),
            due_time=time(10, 0),
        )
        task_linked = Task(
            owner_id=test_user.id,
            title="Linked calendar task",
            due_date=date(2026, 10, 6),
            due_time=time(11, 0),
        )
        session.add_all([task_plain, task_linked])
        await session.flush()
        session.add(
            CalendarRequest(
                owner_id=test_user.id,
                task_id=task_linked.id,
                operation="create",
                calendar_external_id="family",
                title=task_linked.title,
                starts_at=now,
                ends_at=now + timedelta(minutes=30),
                status=CalendarRequestStatus.DONE.value,
                external_event_id="event-1",
                idempotency_key="linked-1",
            )
        )
        await session.commit()

    response = await client.get(f"/calendar/{test_user.calendar_token}.ics")
    assert response.status_code == 200
    assert "Plain feed task" in response.text
    assert "Linked calendar task" not in response.text
