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


async def test_tags_require_auth(client: AsyncClient) -> None:
    response = await client.get("/tags")
    assert response.status_code == 401


async def test_create_update_list_and_soft_delete_tag(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login(client, csrf_headers, test_user.email, "correct-password")
    headers = await csrf_headers(client)

    created = await client.post("/tags", json={"name": "urgentní"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["name"] == "urgentní"
    assert created.json()["owner_id"] == str(test_user.id)

    updated = await client.patch(
        f"/tags/{created.json()['id']}", json={"name": "čeká na odpověď"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "čeká na odpověď"

    listed = await client.get("/tags")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [created.json()["id"]]

    deleted = await client.delete(f"/tags/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get("/tags")).json()["items"] == []

    from app.models.tag import Tag

    async with TestSessionLocal() as session:
        row = await session.execute(select(Tag).where(Tag.id == uuid.UUID(created.json()["id"])))
        assert row.scalar_one().deleted_at is not None


async def test_tag_list_is_filtered_by_owner(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    from app.models.tag import Tag

    async with TestSessionLocal() as session:
        other_user = User(
            email="other-tag-owner@example.com",
            hashed_password=hash_password("secret"),
            display_name="Other Owner",
        )
        session.add(other_user)
        await session.flush()
        session.add(Tag(owner_id=other_user.id, name="cizí"))
        await session.commit()

    await _login(client, csrf_headers, test_user.email, "correct-password")
    response = await client.get("/tags")

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_task_tag_many_to_many_mapping(test_user: User) -> None:
    from app.models.tag import Tag
    from app.models.task import Task, task_tags

    async with TestSessionLocal() as session:
        tag = Tag(owner_id=test_user.id, name="ranč")
        task = Task(owner_id=test_user.id, title="Vyřídit na ranči")
        session.add_all([tag, task])
        await session.flush()
        await session.execute(task_tags.insert().values(task_id=task.id, tag_id=tag.id))
        await session.commit()

        rows = await session.execute(
            select(task_tags.c.task_id, task_tags.c.tag_id).where(task_tags.c.task_id == task.id)
        )
        assert rows.one() == (task.id, tag.id)
