from datetime import UTC, datetime, tzinfo

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User
from tests.conftest import CsrfHeaders, TestSessionLocal


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, test_user: User) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def test_challenges_require_auth(client: AsyncClient) -> None:
    response = await client.get("/challenges")

    assert response.status_code == 401


async def test_create_list_and_get_daily_action_challenge(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    category = await client.post(
        "/categories", json={"name": "Zdraví", "color": "#22c55e", "icon": "heart"}, headers=headers
    )
    vision = await client.post(
        "/visions", json={"title": "Být fit", "horizon": "1y"}, headers=headers
    )

    created = await client.post(
        "/challenges",
        json={
            "title": "Švihadlo",
            "description": "Každý den aspoň pár minut.",
            "type": "daily_action",
            "category_id": category.json()["id"],
            "vision_id": vision.json()["id"],
            "started_at": "2026-09-01T00:00:00+02:00",
            "target_days": 100,
            "allowed_gap_days": 1,
            "is_active": True,
            "color": "#f97316",
            "icon": "activity",
        },
        headers=headers,
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "Švihadlo"
    assert payload["type"] == "daily_action"
    assert payload["category_id"] == category.json()["id"]
    assert payload["vision_id"] == vision.json()["id"]
    assert payload["target_days"] == 100
    assert payload["allowed_gap_days"] == 1
    assert payload["current_streak"] == 0
    assert payload["longest_streak"] == 0
    assert payload["owner_id"] == str(test_user.id)

    listed = await client.get("/challenges")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [payload["id"]]

    fetched = await client.get(f"/challenges/{payload['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == payload["id"]


async def test_check_in_same_date_is_idempotent_and_recalculates_streak(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 5, 9, 0, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "Čtení",
            "type": "daily_action",
            "started_at": "2026-09-01T00:00:00+02:00",
            "color": "#3b82f6",
            "icon": "book-open",
        },
        headers=headers,
    )
    assert challenge.status_code == 201
    challenge_id = challenge.json()["id"]

    first = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-05", "value": 20, "note": "Ráno", "is_relapse": False},
        headers=headers,
    )
    second = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-05", "value": 30, "note": "Opraveno", "is_relapse": False},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["check_in"]["id"] == first.json()["check_in"]["id"]
    assert second.json()["check_in"]["value"] == 30
    assert second.json()["check_in"]["note"] == "Opraveno"
    assert second.json()["current_streak"] == 1
    assert second.json()["longest_streak"] == 1

    from app.models.challenge import CheckIn

    async with TestSessionLocal() as session:
        rows = (await session.execute(select(CheckIn))).scalars().all()
    assert len(rows) == 1


async def test_daily_action_allowed_gap_keeps_streak_alive(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 5, 9, 0, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "3× týdně běh",
            "type": "daily_action",
            "started_at": "2026-09-01T00:00:00+02:00",
            "allowed_gap_days": 1,
        },
        headers=headers,
    )
    challenge_id = challenge.json()["id"]

    first = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-01"},
        headers=headers,
    )
    second = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-03"},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["current_streak"] == 3
    assert second.json()["longest_streak"] == 3


async def test_daily_action_rejects_future_and_too_old_backfill_dates(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={"title": "Kardio", "type": "daily_action"},
        headers=headers,
    )
    challenge_id = challenge.json()["id"]

    valid_backfill = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-03"},
        headers=headers,
    )
    too_old = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-02"},
        headers=headers,
    )
    future = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-11"},
        headers=headers,
    )

    assert valid_backfill.status_code == 201
    assert too_old.status_code == 400
    assert "too far" in too_old.json()["detail"]
    assert future.status_code == 400
    assert "future" in future.json()["detail"]


async def test_daily_action_pause_freezes_streak_instead_of_breaking_it(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 5, 10, 0, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "Švihadlo po nemoci",
            "type": "daily_action",
            "started_at": "2026-09-01T00:00:00+02:00",
            "allowed_gap_days": 0,
        },
        headers=headers,
    )
    challenge_id = challenge.json()["id"]
    for day in ["2026-09-01", "2026-09-02"]:
        response = await client.post(
            f"/challenges/{challenge_id}/check-in", json={"date": day}, headers=headers
        )
        assert response.status_code == 201

    pause = await client.post(
        f"/challenges/{challenge_id}/pauses",
        json={"start_date": "2026-09-03", "end_date": "2026-09-04", "note": "nemoc"},
        headers=headers,
    )

    assert pause.status_code == 201
    fetched = await client.get(f"/challenges/{challenge_id}")
    assert fetched.status_code == 200
    assert fetched.json()["current_streak"] == 2
    assert fetched.json()["longest_streak"] == 2

    resumed = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-05"},
        headers=headers,
    )

    assert resumed.status_code == 201
    assert resumed.json()["current_streak"] == 3
    assert resumed.json()["longest_streak"] == 3


async def test_abstinence_rejects_success_check_in_and_relapse_resets_current_streak(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "Bez cukru",
            "type": "abstinence",
            "started_at": "2026-09-01T00:00:00+02:00",
        },
        headers=headers,
    )
    challenge_id = challenge.json()["id"]

    success_attempt = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-03", "is_relapse": False},
        headers=headers,
    )
    first_relapse = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-04", "is_relapse": True, "note": "dort"},
        headers=headers,
    )
    second_relapse = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-10", "is_relapse": True, "note": "oslava"},
        headers=headers,
    )

    assert success_attempt.status_code == 400
    assert "relapse" in success_attempt.json()["detail"]
    assert first_relapse.status_code == 201
    assert first_relapse.json()["current_streak"] == 6
    assert first_relapse.json()["longest_streak"] == 6
    assert second_relapse.status_code == 201
    assert second_relapse.json()["current_streak"] == 0
    assert second_relapse.json()["longest_streak"] == 6


async def test_abstinence_pause_freezes_elapsed_time(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "Bez alkoholu",
            "type": "abstinence",
            "started_at": "2026-09-01T00:00:00+02:00",
        },
        headers=headers,
    )
    challenge_id = challenge.json()["id"]

    pause = await client.post(
        f"/challenges/{challenge_id}/pauses",
        json={"start_date": "2026-09-03", "end_date": "2026-09-04", "note": "dovolená"},
        headers=headers,
    )
    fetched = await client.get(f"/challenges/{challenge_id}")

    assert pause.status_code == 201
    assert fetched.status_code == 200
    assert fetched.json()["current_streak"] == 3
    assert fetched.json()["longest_streak"] == 3


async def test_challenge_stats_include_streak_totals_and_success_rates(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "Ranní mobilita",
            "type": "daily_action",
            "started_at": "2026-09-01T00:00:00+02:00",
        },
        headers=headers,
    )
    challenge_id = challenge.json()["id"]
    pause = await client.post(
        f"/challenges/{challenge_id}/pauses",
        json={"start_date": "2026-09-05", "end_date": "2026-09-05"},
        headers=headers,
    )
    assert pause.status_code == 201
    for day in ["2026-09-08", "2026-09-09", "2026-09-10"]:
        response = await client.post(
            f"/challenges/{challenge_id}/check-in", json={"date": day}, headers=headers
        )
        assert response.status_code == 201

    stats = await client.get(f"/challenges/{challenge_id}/stats")

    assert stats.status_code == 200
    assert stats.json() == {
        "current_streak": 3,
        "longest_streak": 3,
        "total_count": 3,
        "success_rate_30": 33.33,
        "success_rate_90": 33.33,
        "active_days_30": 9,
        "active_days_90": 9,
    }


async def test_challenge_heatmap_returns_year_days_with_values_notes_relapses_and_pauses(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "Čtení s heatmapou",
            "type": "daily_action",
            "started_at": "2026-01-01T00:00:00+01:00",
        },
        headers=headers,
    )
    challenge_id = challenge.json()["id"]
    checked = await client.post(
        f"/challenges/{challenge_id}/check-in",
        json={"date": "2026-09-05", "value": 45, "note": "kapitola 3"},
        headers=headers,
    )
    pause = await client.post(
        f"/challenges/{challenge_id}/pauses",
        json={"start_date": "2026-09-06", "end_date": "2026-09-07", "note": "výlet"},
        headers=headers,
    )
    assert checked.status_code == 201
    assert pause.status_code == 201

    heatmap = await client.get(f"/challenges/{challenge_id}/heatmap?year=2026")

    assert heatmap.status_code == 200
    payload = heatmap.json()
    assert payload["year"] == 2026
    assert len(payload["days"]) == 365
    day = next(item for item in payload["days"] if item["date"] == "2026-09-05")
    assert day == {
        "date": "2026-09-05",
        "has_check_in": True,
        "value": 45,
        "note": "kapitola 3",
        "is_relapse": False,
        "is_paused": False,
        "intensity": 4,
    }
    paused = next(item for item in payload["days"] if item["date"] == "2026-09-06")
    assert paused["has_check_in"] is False
    assert paused["is_paused"] is True
    assert paused["intensity"] == 0


async def test_check_in_without_date_uses_user_timezone_not_utc(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_user.timezone = "Europe/Prague"
    async with TestSessionLocal() as session:
        stored = await session.get(User, test_user.id)
        assert stored is not None
        stored.timezone = "Europe/Prague"
        await session.commit()

    class FixedDateTime:
        @staticmethod
        def now(tz: tzinfo | None = None) -> datetime:
            value = datetime(2026, 9, 5, 22, 30, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    import app.services.challenge_service as challenge_service

    monkeypatch.setattr(challenge_service, "datetime", FixedDateTime)
    headers = await _login(client, csrf_headers, test_user)
    challenge = await client.post(
        "/challenges",
        json={
            "title": "Pozdní kardio",
            "type": "daily_action",
            "started_at": "2026-09-01T00:00:00+02:00",
        },
        headers=headers,
    )

    response = await client.post(
        f"/challenges/{challenge.json()['id']}/check-in", json={}, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["check_in"]["date"] == "2026-09-06"
