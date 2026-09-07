from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskUpdate
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


async def test_task_patch_requires_if_match_and_increments_version(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    created = await client.post("/tasks", json={"title": "Versioned"}, headers=headers)
    assert created.status_code == 201
    task = created.json()
    assert task["version"] == 1
    assert task["created_by"] == "user"
    assert task["updated_by"] == "user"
    assert task["api_key_id"] is None

    missing = await client.patch(
        f"/tasks/{task['id']}", json={"title": "No match"}, headers=headers
    )
    assert missing.status_code == 428
    assert missing.json()["detail"]["code"] == "if_match_required"

    updated = await client.patch(
        f"/tasks/{task['id']}",
        json={"title": "Versioned updated"},
        headers={**headers, "If-Match": str(task["version"])},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["title"] == "Versioned updated"


async def test_task_patch_version_conflict_returns_current_state(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    created = await client.post("/tasks", json={"title": "Conflict"}, headers=headers)
    task = created.json()
    first = await client.patch(
        f"/tasks/{task['id']}",
        json={"title": "First"},
        headers={**headers, "If-Match": "1"},
    )
    assert first.status_code == 200

    conflict = await client.patch(
        f"/tasks/{task['id']}",
        json={"title": "Second stale"},
        headers={**headers, "If-Match": "1"},
    )
    assert conflict.status_code == 409
    detail = conflict.json()["detail"]
    assert detail["code"] == "version_conflict"
    assert detail["current_state"]["title"] == "First"
    assert detail["current_state"]["version"] == 2


async def test_task_delete_requires_matching_version(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    created = await client.post("/tasks", json={"title": "Delete version"}, headers=headers)
    task = created.json()

    missing = await client.delete(f"/tasks/{task['id']}", headers=headers)
    assert missing.status_code == 428

    stale = await client.delete(f"/tasks/{task['id']}", headers={**headers, "If-Match": "99"})
    assert stale.status_code == 409
    assert stale.json()["detail"]["current_state"]["version"] == 1

    deleted = await client.delete(
        f"/tasks/{task['id']}", headers={**headers, "If-Match": str(task["version"])}
    )
    assert deleted.status_code == 204


async def test_agent_update_recent_user_edit_is_blocked(test_user: User) -> None:
    from app.services import task_service
    from app.services.concurrency import FreshUserEditConflict, MutationActor

    async with TestSessionLocal() as session:
        task = Task(
            owner_id=test_user.id,
            title="Fresh human edit",
            version=3,
            created_by="user",
            updated_by="user",
            updated_at=datetime.now(UTC),
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        with pytest.raises(FreshUserEditConflict) as exc_info:
            await task_service.update_task(
                session,
                test_user,
                task.id,
                TaskUpdate(title="Agent overwrite"),
                expected_version=3,
                actor=MutationActor.AGENT,
            )
        assert exc_info.value.current_state["id"] == str(task.id)
        assert exc_info.value.current_state["version"] == 3
        assert "recently edited by user" in exc_info.value.message
