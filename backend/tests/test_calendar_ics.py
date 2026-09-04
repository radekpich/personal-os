from datetime import date, time

from httpx import AsyncClient

from app.models.task import RecurrenceMode, Task, TaskPriority, TaskStatus
from app.models.user import User
from tests.conftest import CsrfHeaders, TestSessionLocal


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, user: User) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def test_calendar_feed_is_public_by_token_and_exports_vevents(test_user: User) -> None:
    async with TestSessionLocal() as session:
        session.add_all(
            [
                Task(owner_id=test_user.id, title="Celodenní úkol", due_date=date(2026, 9, 10)),
                Task(
                    owner_id=test_user.id,
                    title="Časovaný úkol",
                    status=TaskStatus.TODO.value,
                    priority=TaskPriority.HIGH.value,
                    due_date=date(2026, 9, 10),
                    due_time=time(14, 0),
                    estimate_minutes=45,
                    description="tajný detail se nesmí exportovat",
                ),
                Task(owner_id=test_user.id, title="Bez termínu", due_date=None),
            ]
        )
        await session.commit()

    from httpx import ASGITransport

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("10.6.0.1", 123)), base_url="https://testserver"
    ) as client:
        response = await client.get(f"/calendar/{test_user.calendar_token}.ics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/calendar; charset=utf-8"
    assert "no-store" in response.headers["cache-control"]
    body = response.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VTIMEZONE" in body
    assert "TZID:Europe/Prague" in body
    assert body.count("BEGIN:VEVENT") == 2
    assert "BEGIN:VTODO" not in body
    assert "SUMMARY:Celodenní úkol" in body
    assert "DTSTART;VALUE=DATE:20260910" in body
    assert "SUMMARY:Časovaný úkol" in body
    assert "DTSTART;TZID=Europe/Prague:20260910T140000" in body
    assert "DTEND;TZID=Europe/Prague:20260910T144500" in body
    assert "tajný detail" not in body
    assert "UID:task-" in body


async def test_calendar_feed_exports_rrule_as_single_event(test_user: User) -> None:
    async with TestSessionLocal() as session:
        session.add(
            Task(
                owner_id=test_user.id,
                title="Krmení zvířat",
                due_date=date(2026, 9, 7),
                due_time=time(8, 0),
                recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
                recurrence_mode=RecurrenceMode.FIXED.value,
            )
        )
        await session.commit()

    from httpx import ASGITransport

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("10.6.0.2", 123)), base_url="https://testserver"
    ) as client:
        response = await client.get(f"/calendar/{test_user.calendar_token}.ics")

    assert response.status_code == 200
    body = response.text
    assert body.count("BEGIN:VEVENT") == 1
    assert "RRULE:FREQ=WEEKLY;BYDAY=MO" in body


async def test_calendar_feed_rejects_unknown_token(client: AsyncClient) -> None:
    response = await client.get("/calendar/not-a-real-token.ics")
    assert response.status_code == 404


async def test_regenerate_calendar_token_requires_auth_and_csrf(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    original_token = test_user.calendar_token
    unauth = await client.post("/calendar/regenerate-token")
    assert unauth.status_code == 403

    headers = await _login(client, csrf_headers, test_user)
    missing_csrf = await client.post("/calendar/regenerate-token")
    assert missing_csrf.status_code == 403

    response = await client.post("/calendar/regenerate-token", headers=headers)
    assert response.status_code == 200
    new_token = response.json()["calendar_token"]
    assert new_token != original_token
    assert len(new_token) >= 32

    old_feed = await client.get(f"/calendar/{original_token}.ics")
    new_feed = await client.get(f"/calendar/{new_token}.ics")
    assert old_feed.status_code == 404
    assert new_feed.status_code == 200
