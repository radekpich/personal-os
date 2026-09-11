from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from httpx import AsyncClient

from app.models.user import User
from tests.conftest import CsrfHeaders


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, user: User) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def test_create_recurring_task_exposes_rrule_and_mode(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)

    response = await client.post(
        "/tasks",
        json={
            "title": "Každé pondělí fakturace",
            "status": "todo",
            "due_date": "2026-09-07",
            "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",
            "recurrence_mode": "fixed",
        },
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=MO"
    assert payload["recurrence_mode"] == "fixed"
    assert payload["recurrence_template_id"] is None


async def test_fixed_recurring_task_generates_next_instance_from_rule(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    created = await client.post(
        "/tasks",
        json={
            "title": "Krmení zvířat",
            "status": "todo",
            "due_date": "2026-09-07",
            "due_time": "08:00:00",
            "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",
            "recurrence_mode": "fixed",
        },
        headers=headers,
    )
    assert created.status_code == 201

    done = await client.patch(
        f"/tasks/{created.json()['id']}",
        json={"status": "done"},
        headers={**headers, "If-Match": str(created.json()["version"])},
    )
    assert done.status_code == 200

    listed = await client.get("/tasks", params={"status": "todo"})
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    next_task = items[0]
    assert next_task["title"] == "Krmení zvířat"
    assert next_task["due_date"] == "2026-09-14"
    assert next_task["due_time"] == "08:00:00"
    assert next_task["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=MO"
    assert next_task["recurrence_mode"] == "fixed"
    assert next_task["recurrence_template_id"] == created.json()["id"]


async def test_after_completion_recurring_task_generates_from_completed_at(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    created = await client.post(
        "/tasks",
        json={
            "title": "Vyměnit podestýlku",
            "status": "todo",
            "due_date": "2026-09-01",
            "recurrence_rule": "FREQ=DAILY;INTERVAL=7",
            "recurrence_mode": "after_completion",
        },
        headers=headers,
    )
    assert created.status_code == 201

    client_supplied_completed_at = datetime(2026, 9, 10, 12, 0, tzinfo=UTC).isoformat()
    done = await client.patch(
        f"/tasks/{created.json()['id']}",
        json={"status": "done", "completed_at": client_supplied_completed_at},
        headers={**headers, "If-Match": str(created.json()["version"])},
    )
    assert done.status_code == 200
    assert done.json()["completed_at"] != client_supplied_completed_at
    completed_day = datetime.fromisoformat(done.json()["completed_at"]).astimezone(
        ZoneInfo("Europe/Prague")
    ).date()

    listed = await client.get("/tasks", params={"status": "todo"})
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["due_date"] == (completed_day + timedelta(days=7)).isoformat()
    assert items[0]["recurrence_template_id"] == created.json()["id"]


async def test_invalid_rrule_is_rejected(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)

    response = await client.post(
        "/tasks",
        json={
            "title": "Špatné opakování",
            "recurrence_rule": "BYDAY=MO",
            "recurrence_mode": "fixed",
        },
        headers=headers,
    )

    assert response.status_code == 422
