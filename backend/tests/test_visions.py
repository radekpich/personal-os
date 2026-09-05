from httpx import AsyncClient
from sqlalchemy import event, text

from app.models.user import User
from tests.conftest import CsrfHeaders, engine


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


async def test_vision_rejects_self_parent(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    created = await client.post("/visions", json={"title": "Životní sen"}, headers=headers)
    vision_id = created.json()["id"]

    response = await client.patch(
        f"/visions/{vision_id}", json={"parent_id": vision_id}, headers=headers
    )

    assert response.status_code == 400
    assert "parent" in response.json()["detail"]


async def test_vision_rejects_parent_cycle(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    root = await client.post("/visions", json={"title": "Sen"}, headers=headers)
    child = await client.post(
        "/visions", json={"title": "Cíl", "parent_id": root.json()["id"]}, headers=headers
    )
    grandchild = await client.post(
        "/visions",
        json={"title": "Milník", "parent_id": child.json()["id"]},
        headers=headers,
    )

    response = await client.patch(
        f"/visions/{root.json()['id']}",
        json={"parent_id": grandchild.json()["id"]},
        headers=headers,
    )

    assert response.status_code == 400
    assert "cycle" in response.json()["detail"]


async def test_vision_limits_tree_depth_to_four_levels(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    root = await client.post("/visions", json={"title": "Level 1"}, headers=headers)
    level2 = await client.post(
        "/visions", json={"title": "Level 2", "parent_id": root.json()["id"]}, headers=headers
    )
    level3 = await client.post(
        "/visions", json={"title": "Level 3", "parent_id": level2.json()["id"]}, headers=headers
    )
    level4 = await client.post(
        "/visions", json={"title": "Level 4", "parent_id": level3.json()["id"]}, headers=headers
    )

    assert level4.status_code == 201

    level5 = await client.post(
        "/visions", json={"title": "Level 5", "parent_id": level4.json()["id"]}, headers=headers
    )

    assert level5.status_code == 400
    assert "depth" in level5.json()["detail"]


async def test_vision_tree_returns_nested_tree_with_single_vision_select(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    root = await client.post("/visions", json={"title": "Sen", "position": 2}, headers=headers)
    child = await client.post(
        "/visions",
        json={"title": "Cíl", "parent_id": root.json()["id"], "position": 1},
        headers=headers,
    )
    await client.post(
        "/visions",
        json={"title": "Milník", "parent_id": child.json()["id"], "position": 1},
        headers=headers,
    )

    vision_selects: list[str] = []

    def before_cursor_execute(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        normalized = " ".join(statement.lower().split())
        if " from visions" in normalized:
            vision_selects.append(normalized)

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        response = await client.get("/visions/tree")
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200
    tree = response.json()["items"]
    assert len(tree) == 1
    assert tree[0]["title"] == "Sen"
    assert tree[0]["children"][0]["title"] == "Cíl"
    assert tree[0]["children"][0]["children"][0]["title"] == "Milník"
    assert len(vision_selects) == 1


async def test_vision_progress_counts_linked_tasks_and_stagnation(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    vision = await client.post("/visions", json={"title": "Rozjet Ranč OS"}, headers=headers)
    vision_id = vision.json()["id"]
    task1 = await client.post(
        "/tasks", json={"title": "Hotový krok", "vision_id": vision_id}, headers=headers
    )
    await client.post(
        "/tasks", json={"title": "Další krok", "vision_id": vision_id}, headers=headers
    )
    await client.patch(f"/tasks/{task1.json()['id']}", json={"status": "done"}, headers=headers)

    response = await client.get(f"/visions/{vision_id}/progress")

    assert response.status_code == 200
    data = response.json()
    assert data["vision_id"] == vision_id
    assert data["total_tasks"] == 2
    assert data["done_tasks"] == 1
    assert data["last_activity_at"] is not None
    assert data["stagnation_days"] == 0


async def test_stagnating_visions_returns_items_without_recent_task_movement(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    stale = await client.post("/visions", json={"title": "Stará vize"}, headers=headers)
    fresh = await client.post("/visions", json={"title": "Čerstvá vize"}, headers=headers)
    await client.post(
        "/tasks", json={"title": "Starý pohyb", "vision_id": stale.json()["id"]}, headers=headers
    )
    await client.post(
        "/tasks", json={"title": "Čerstvý pohyb", "vision_id": fresh.json()["id"]}, headers=headers
    )
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE tasks SET updated_at = datetime('now', '-10 days') "
                "WHERE title = 'Starý pohyb'"
            )
        )

    response = await client.get("/visions/stagnating?days=7")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["vision"]["title"] for item in items] == ["Stará vize"]
    assert items[0]["progress"]["total_tasks"] == 1
    assert items[0]["progress"]["stagnation_days"] >= 7
