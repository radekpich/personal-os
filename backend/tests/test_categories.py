import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.models.user import User
from tests.conftest import CsrfHeaders, TestSessionLocal


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, email: str, password: str) -> None:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=headers,
    )
    assert response.status_code == 200


async def test_categories_require_auth(client: AsyncClient) -> None:
    response = await client.get("/categories")
    assert response.status_code == 401


async def test_create_and_list_category_for_current_owner(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login(client, csrf_headers, test_user.email, "correct-password")
    headers = await csrf_headers(client)

    created = await client.post(
        "/categories",
        json={
            "name": "Stavba",
            "color": "#F97316",
            "icon": "hammer",
            "position": 10,
        },
        headers=headers,
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["name"] == "Stavba"
    assert payload["color"] == "#F97316"
    assert payload["icon"] == "hammer"
    assert payload["parent_id"] is None
    assert payload["position"] == 10
    assert payload["is_archived"] is False

    listed = await client.get("/categories")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [payload["id"]]


async def test_category_list_is_filtered_by_owner(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    from app.models.category import Category

    async with TestSessionLocal() as session:
        other_user = User(
            email="other-category-owner@example.com",
            hashed_password=hash_password("secret"),
            display_name="Other Owner",
        )
        session.add(other_user)
        await session.flush()
        session.add(
            Category(
                owner_id=other_user.id,
                name="Cizí",
                color="#000000",
                icon="lock",
                position=1,
            )
        )
        await session.commit()

    await _login(client, csrf_headers, test_user.email, "correct-password")
    response = await client.get("/categories")

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_category_allows_only_two_levels(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login(client, csrf_headers, test_user.email, "correct-password")
    headers = await csrf_headers(client)

    parent = await client.post(
        "/categories",
        json={"name": "Stavba", "color": "#F97316", "icon": "hammer"},
        headers=headers,
    )
    child = await client.post(
        "/categories",
        json={
            "name": "Hrubá stavba",
            "color": "#FDBA74",
            "icon": "bricks",
            "parent_id": parent.json()["id"],
        },
        headers=headers,
    )
    grandchild = await client.post(
        "/categories",
        json={
            "name": "Třetí úroveň",
            "color": "#FED7AA",
            "icon": "ban",
            "parent_id": child.json()["id"],
        },
        headers=headers,
    )

    assert child.status_code == 201
    assert grandchild.status_code == 400


async def test_soft_delete_category_hides_it_from_list(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login(client, csrf_headers, test_user.email, "correct-password")
    headers = await csrf_headers(client)
    created = await client.post(
        "/categories",
        json={"name": "Rodina", "color": "#22C55E", "icon": "home"},
        headers=headers,
    )

    deleted = await client.delete(f"/categories/{created.json()['id']}", headers=headers)
    listed = await client.get("/categories")

    assert deleted.status_code == 204
    assert listed.status_code == 200
    assert listed.json()["items"] == []

    from app.models.category import Category

    async with TestSessionLocal() as session:
        row = await session.execute(
            select(Category).where(Category.id == uuid.UUID(created.json()["id"]))
        )
        assert row.scalar_one().deleted_at is not None
