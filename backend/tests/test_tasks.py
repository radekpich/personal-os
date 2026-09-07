import uuid
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.models.category import Category
from app.models.context import Context
from app.models.tag import Tag
from app.models.task import Task
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


async def _login_test_user(client: AsyncClient, csrf_headers: CsrfHeaders, test_user: User) -> None:
    await _login(client, csrf_headers, test_user.email, "correct-password")


async def test_tasks_require_auth(client: AsyncClient) -> None:
    response = await client.get("/tasks")
    assert response.status_code == 401


async def test_quick_create_task_from_plain_text(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)
    headers["Content-Type"] = "text/plain"

    response = await client.post("/tasks/quick", content="Koupit krmivo", headers=headers)

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Koupit krmivo"
    assert payload["status"] == "inbox"
    assert payload["priority"] == "none"
    assert payload["owner_id"] == str(test_user.id)
    assert payload["tags"] == []


async def test_quick_create_task_requires_csrf(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)

    response = await client.post(
        "/tasks/quick", content="bez CSRF", headers={"Content-Type": "text/plain"}
    )

    assert response.status_code == 403


async def test_quick_create_task_rejects_empty_body(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)
    headers["Content-Type"] = "text/plain"

    response = await client.post("/tasks/quick", content="   ", headers=headers)

    assert response.status_code == 400


async def test_create_task_with_full_fields_and_tags(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    async with TestSessionLocal() as session:
        category = Category(owner_id=test_user.id, name="Stavba", color="#F97316", icon="hammer")
        context = Context(owner_id=test_user.id, name="@ranč")
        tag = Tag(owner_id=test_user.id, name="urgentní")
        session.add_all([category, context, tag])
        await session.commit()
        await session.refresh(category)
        await session.refresh(context)
        await session.refresh(tag)

    response = await client.post(
        "/tasks",
        json={
            "title": "Zkontrolovat zdivo",
            "description": "Zkontrolovat **zdivo** a rozvody",
            "status": "todo",
            "priority": "high",
            "due_date": "2026-09-10",
            "due_time": "14:30:00",
            "estimate_minutes": 45,
            "category_id": str(category.id),
            "context_id": str(context.id),
            "position": 5,
            "tag_ids": [str(tag.id)],
        },
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Zkontrolovat zdivo"
    assert payload["status"] == "todo"
    assert payload["priority"] == "high"
    assert payload["due_date"] == "2026-09-10"
    assert payload["due_time"] == "14:30:00"
    assert payload["estimate_minutes"] == 45
    assert payload["category_id"] == str(category.id)
    assert payload["context_id"] == str(context.id)
    assert payload["position"] == 5
    assert [t["id"] for t in payload["tags"]] == [str(tag.id)]
    assert payload["completed_at"] is None


async def test_create_task_rejects_foreign_category(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    async with TestSessionLocal() as session:
        other_user = User(
            email="other-task-owner@example.com",
            hashed_password=hash_password("secret"),
            display_name="Other Owner",
        )
        session.add(other_user)
        await session.flush()
        foreign_category = Category(
            owner_id=other_user.id, name="Cizí", color="#000000", icon="lock"
        )
        session.add(foreign_category)
        await session.commit()
        await session.refresh(foreign_category)

    response = await client.post(
        "/tasks",
        json={"title": "Test", "category_id": str(foreign_category.id)},
        headers=headers,
    )

    assert response.status_code == 404


async def test_create_task_rejects_foreign_tag(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    async with TestSessionLocal() as session:
        other_user = User(
            email="other-task-tag-owner@example.com",
            hashed_password=hash_password("secret"),
            display_name="Other Owner",
        )
        session.add(other_user)
        await session.flush()
        foreign_tag = Tag(owner_id=other_user.id, name="cizí")
        session.add(foreign_tag)
        await session.commit()
        await session.refresh(foreign_tag)

    response = await client.post(
        "/tasks",
        json={"title": "Test", "tag_ids": [str(foreign_tag.id)]},
        headers=headers,
    )

    assert response.status_code == 404


async def test_get_update_and_soft_delete_task(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    created = await client.post("/tasks", json={"title": "Napsat report"}, headers=headers)
    task_id = created.json()["id"]

    fetched = await client.get(f"/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Napsat report"

    done_update = await client.patch(
        f"/tasks/{task_id}",
        json={"status": "done"},
        headers={**headers, "If-Match": str(created.json()["version"])},
    )
    assert done_update.status_code == 200
    assert done_update.json()["status"] == "done"
    assert done_update.json()["completed_at"] is not None

    reopened = await client.patch(
        f"/tasks/{task_id}",
        json={"status": "todo"},
        headers={**headers, "If-Match": str(done_update.json()["version"])},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "todo"
    assert reopened.json()["completed_at"] is None

    deleted = await client.delete(
        f"/tasks/{task_id}", headers={**headers, "If-Match": str(reopened.json()["version"])}
    )
    assert deleted.status_code == 204

    missing = await client.get(f"/tasks/{task_id}")
    assert missing.status_code == 404

    async with TestSessionLocal() as session:
        row = await session.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
        assert row.scalar_one().deleted_at is not None


async def test_task_owner_isolation(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    async with TestSessionLocal() as session:
        other_user = User(
            email="other-task-isolation@example.com",
            hashed_password=hash_password("secret"),
            display_name="Other Owner",
        )
        session.add(other_user)
        await session.flush()
        foreign_task = Task(owner_id=other_user.id, title="Cizí úkol")
        session.add(foreign_task)
        await session.commit()
        await session.refresh(foreign_task)

    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    get_response = await client.get(f"/tasks/{foreign_task.id}")
    assert get_response.status_code == 404

    patch_response = await client.patch(
        f"/tasks/{foreign_task.id}",
        json={"title": "hack"},
        headers={**headers, "If-Match": "1"},
    )
    assert patch_response.status_code == 404

    delete_response = await client.delete(
        f"/tasks/{foreign_task.id}", headers={**headers, "If-Match": "1"}
    )
    assert delete_response.status_code == 404

    listed = await client.get("/tasks")
    assert listed.json()["items"] == []
    assert listed.json()["total"] == 0


async def test_list_tasks_filters_and_pagination(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    async with TestSessionLocal() as session:
        category = Category(owner_id=test_user.id, name="Ranč", color="#123456", icon="barn")
        context = Context(owner_id=test_user.id, name="@ranč")
        tag = Tag(owner_id=test_user.id, name="zvířata")
        session.add_all([category, context, tag])
        await session.commit()
        await session.refresh(category)
        await session.refresh(context)
        await session.refresh(tag)

    for i in range(3):
        await client.post(
            "/tasks",
            json={"title": f"Krmit kozy {i}", "status": "todo", "due_date": "2026-09-10"},
            headers=headers,
        )

    tagged = await client.post(
        "/tasks",
        json={
            "title": "Nakrmit slepice",
            "status": "todo",
            "category_id": str(category.id),
            "context_id": str(context.id),
            "tag_ids": [str(tag.id)],
            "due_date": "2026-09-11",
        },
        headers=headers,
    )
    tagged_id = tagged.json()["id"]

    await client.post("/tasks", json={"title": "Something done", "status": "done"}, headers=headers)

    by_status = await client.get("/tasks", params={"status": "done"})
    assert by_status.json()["total"] == 1

    by_category = await client.get("/tasks", params={"category_id": str(category.id)})
    assert [t["id"] for t in by_category.json()["items"]] == [tagged_id]

    by_context = await client.get("/tasks", params={"context_id": str(context.id)})
    assert [t["id"] for t in by_context.json()["items"]] == [tagged_id]

    by_tag = await client.get("/tasks", params={"tag_ids": [str(tag.id)]})
    assert [t["id"] for t in by_tag.json()["items"]] == [tagged_id]

    by_due_range = await client.get(
        "/tasks", params={"due_from": "2026-09-11", "due_to": "2026-09-11"}
    )
    assert [t["id"] for t in by_due_range.json()["items"]] == [tagged_id]

    by_q = await client.get("/tasks", params={"q": "slepice"})
    assert [t["id"] for t in by_q.json()["items"]] == [tagged_id]

    page1 = await client.get("/tasks", params={"page": 1, "page_size": 2})
    assert len(page1.json()["items"]) == 2
    assert page1.json()["total"] == 5
    assert page1.json()["page"] == 1

    page2 = await client.get("/tasks", params={"page": 2, "page_size": 2})
    assert len(page2.json()["items"]) == 2

    page3 = await client.get("/tasks", params={"page": 3, "page_size": 2})
    assert len(page3.json()["items"]) == 1


async def test_named_views_use_europe_prague_local_date(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    from zoneinfo import ZoneInfo

    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    today = datetime.now(ZoneInfo("Europe/Prague")).date()
    clearly_overdue = today - timedelta(days=14)
    this_week_day = today + timedelta(days=1) if today.weekday() < 6 else today
    far_future = today + timedelta(days=60)

    inbox_task = await client.post("/tasks", json={"title": "Inbox úkol"}, headers=headers)
    today_task = await client.post(
        "/tasks",
        json={"title": "Dnešní úkol", "status": "todo", "due_date": today.isoformat()},
        headers=headers,
    )
    week_task = await client.post(
        "/tasks",
        json={
            "title": "Tento týden",
            "status": "todo",
            "due_date": this_week_day.isoformat(),
        },
        headers=headers,
    )
    overdue_task = await client.post(
        "/tasks",
        json={"title": "Po termínu", "status": "todo", "due_date": clearly_overdue.isoformat()},
        headers=headers,
    )
    await client.post(
        "/tasks",
        json={"title": "Daleko v budoucnu", "status": "todo", "due_date": far_future.isoformat()},
        headers=headers,
    )
    await client.post(
        "/tasks",
        json={
            "title": "Hotový po termínu",
            "status": "done",
            "due_date": clearly_overdue.isoformat(),
        },
        headers=headers,
    )

    inbox_view = await client.get("/tasks", params={"view": "inbox"})
    assert [t["id"] for t in inbox_view.json()["items"]] == [inbox_task.json()["id"]]

    today_view = await client.get("/tasks", params={"view": "today"})
    expected_today_ids = {today_task.json()["id"]}
    if this_week_day == today:
        expected_today_ids.add(week_task.json()["id"])
    assert {t["id"] for t in today_view.json()["items"]} == expected_today_ids

    week_view = await client.get("/tasks", params={"view": "this_week"})
    week_ids = {t["id"] for t in week_view.json()["items"]}
    assert today_task.json()["id"] in week_ids
    assert week_task.json()["id"] in week_ids
    assert overdue_task.json()["id"] not in week_ids

    overdue_view = await client.get("/tasks", params={"view": "overdue"})
    assert [t["id"] for t in overdue_view.json()["items"]] == [overdue_task.json()["id"]]


async def test_task_tags_can_be_replaced_on_update(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    async with TestSessionLocal() as session:
        tag_a = Tag(owner_id=test_user.id, name="a")
        tag_b = Tag(owner_id=test_user.id, name="b")
        session.add_all([tag_a, tag_b])
        await session.commit()
        await session.refresh(tag_a)
        await session.refresh(tag_b)

    created = await client.post(
        "/tasks", json={"title": "S tagy", "tag_ids": [str(tag_a.id)]}, headers=headers
    )
    assert [t["id"] for t in created.json()["tags"]] == [str(tag_a.id)]

    updated = await client.patch(
        f"/tasks/{created.json()['id']}",
        json={"tag_ids": [str(tag_b.id)]},
        headers={**headers, "If-Match": str(created.json()["version"])},
    )
    assert updated.status_code == 200
    assert [t["id"] for t in updated.json()["tags"]] == [str(tag_b.id)]

    cleared = await client.patch(
        f"/tasks/{created.json()['id']}",
        json={"tag_ids": []},
        headers={**headers, "If-Match": str(updated.json()["version"])},
    )
    assert cleared.json()["tags"] == []


async def test_parent_task_relationship(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    parent = await client.post("/tasks", json={"title": "Rodičovský úkol"}, headers=headers)
    parent_id = parent.json()["id"]

    child = await client.post(
        "/tasks",
        json={"title": "Dílčí úkol", "parent_task_id": parent_id},
        headers=headers,
    )
    assert child.status_code == 201
    assert child.json()["parent_task_id"] == parent_id


async def test_task_cannot_be_its_own_parent(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    created = await client.post("/tasks", json={"title": "Sólo úkol"}, headers=headers)
    task_id = created.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}",
        json={"parent_task_id": task_id},
        headers={**headers, "If-Match": str(created.json()["version"])},
    )
    assert response.status_code == 400


async def test_create_task_requires_csrf(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)

    response = await client.post("/tasks", json={"title": "bez CSRF"})
    assert response.status_code == 403


async def test_invalid_status_value_is_rejected(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    headers = await csrf_headers(client)

    response = await client.post(
        "/tasks", json={"title": "Test", "status": "not-a-status"}, headers=headers
    )
    assert response.status_code == 422


async def test_task_not_found_returns_404(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    await _login_test_user(client, csrf_headers, test_user)
    response = await client.get(f"/tasks/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_task_defaults_have_expected_shape(test_user: User) -> None:
    async with TestSessionLocal() as session:
        task = Task(owner_id=test_user.id, title="Default shape")
        session.add(task)
        await session.commit()
        await session.refresh(task)

        assert task.status == "inbox"
        assert task.priority == "none"
        assert task.position == 0
        assert task.completed_at is None
        assert task.deleted_at is None
        assert isinstance(task.created_at, datetime)


async def test_task_due_date_type_is_date(test_user: User) -> None:
    async with TestSessionLocal() as session:
        task = Task(owner_id=test_user.id, title="Typed due date", due_date=date(2026, 9, 10))
        session.add(task)
        await session.commit()
        await session.refresh(task)
        assert task.due_date == date(2026, 9, 10)


async def test_task_completed_at_utc(test_user: User) -> None:
    async with TestSessionLocal() as session:
        now = datetime.now(UTC)
        task = Task(owner_id=test_user.id, title="Completed", completed_at=now)
        session.add(task)
        await session.commit()
        await session.refresh(task)
        assert task.completed_at is not None
