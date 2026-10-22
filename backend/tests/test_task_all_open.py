from httpx import AsyncClient

from app.models.category import Category
from app.models.user import User
from tests.conftest import CsrfHeaders, TestSessionLocal


async def test_all_tasks_shows_only_open_but_explicit_terminal_filters_work(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    headers = await csrf_headers(client)
    login = await client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-password"},
        headers=headers,
    )
    assert login.status_code == 200
    headers = await csrf_headers(client)
    async with TestSessionLocal() as session:
        category = Category(owner_id=test_user.id, name="KEXO", color="#16A34A", icon="barn")
        session.add(category)
        await session.commit()
        await session.refresh(category)
    for status in ["todo", "in_progress", "blocked", "done", "cancelled"]:
        response = await client.post(
            "/tasks",
            json={"title": status, "status": status, "category_id": str(category.id)},
            headers=headers,
        )
        assert response.status_code == 201
    response = await client.get("/tasks")
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert {t["status"] for t in response.json()["items"]} == {"todo", "in_progress", "blocked"}
    for status in ["done", "cancelled"]:
        response = await client.get("/tasks", params={"status": status})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["status"] == status
