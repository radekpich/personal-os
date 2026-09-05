from httpx import AsyncClient

from app.models.user import User
from tests.conftest import CsrfHeaders


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, test_user: User) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def test_visions_require_auth(client: AsyncClient) -> None:
    response = await client.get("/visions")

    assert response.status_code == 401


async def test_create_list_and_get_vision(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)

    created = await client.post(
        "/visions",
        json={
            "title": "Ranč jako prémiové svatební místo",
            "description": "## Směr\nVybudovat místo, kam se lidi chtějí vracet.",
            "horizon": "5y",
            "status": "active",
            "target_date": "2031-12-31",
            "position": 10,
        },
        headers=headers,
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "Ranč jako prémiové svatební místo"
    assert payload["description"].startswith("## Směr")
    assert payload["parent_id"] is None
    assert payload["horizon"] == "5y"
    assert payload["status"] == "active"
    assert payload["target_date"] == "2031-12-31"
    assert payload["category_id"] is None
    assert payload["position"] == 10
    assert payload["owner_id"] == str(test_user.id)

    listed = await client.get("/visions")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [payload["id"]]

    fetched = await client.get(f"/visions/{payload['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == payload["id"]


async def test_create_task_can_link_to_vision(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    vision = await client.post(
        "/visions",
        json={"title": "Postavit dům", "horizon": "1y"},
        headers=headers,
    )
    assert vision.status_code == 201

    task = await client.post(
        "/tasks",
        json={
            "title": "Domluvit projektanta",
            "status": "todo",
            "vision_id": vision.json()["id"],
        },
        headers=headers,
    )

    assert task.status_code == 201
    assert task.json()["vision_id"] == vision.json()["id"]


async def test_task_rejects_foreign_or_missing_vision(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)

    response = await client.post(
        "/tasks",
        json={"title": "Neplatná vazba", "vision_id": "00000000-0000-4000-8000-000000000999"},
        headers=headers,
    )

    assert response.status_code == 404
