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


async def test_contexts_require_auth(client: AsyncClient) -> None:
    response = await client.get("/contexts")
    assert response.status_code == 401


async def test_create_and_list_context_for_current_owner(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login(client, csrf_headers, test_user.email, "correct-password")
    headers = await csrf_headers(client)

    created = await client.post(
        "/contexts",
        json={"name": "@ranč", "position": 5},
        headers=headers,
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["name"] == "@ranč"
    assert payload["position"] == 5
    assert payload["is_archived"] is False

    listed = await client.get("/contexts")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [payload["id"]]


async def test_context_list_is_filtered_by_owner(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    from app.models.context import Context

    async with TestSessionLocal() as session:
        other_user = User(
            email="other-context-owner@example.com",
            hashed_password=hash_password("secret"),
            display_name="Other Owner",
        )
        session.add(other_user)
        await session.flush()
        session.add(Context(owner_id=other_user.id, name="@cizí", position=1))
        await session.commit()

    await _login(client, csrf_headers, test_user.email, "correct-password")
    response = await client.get("/contexts")

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_update_context_and_soft_delete(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login(client, csrf_headers, test_user.email, "correct-password")
    headers = await csrf_headers(client)
    created = await client.post(
        "/contexts",
        json={"name": "@telefon", "position": 1},
        headers=headers,
    )

    updated = await client.patch(
        f"/contexts/{created.json()['id']}",
        json={"name": "@mobil", "is_archived": True},
        headers=headers,
    )
    deleted = await client.delete(f"/contexts/{created.json()['id']}", headers=headers)
    listed = await client.get("/contexts")

    assert updated.status_code == 200
    assert updated.json()["name"] == "@mobil"
    assert updated.json()["is_archived"] is True
    assert deleted.status_code == 204
    assert listed.json()["items"] == []

    from app.models.context import Context

    async with TestSessionLocal() as session:
        row = await session.execute(
            select(Context).where(Context.id == uuid.UUID(created.json()["id"]))
        )
        assert row.scalar_one().deleted_at is not None
