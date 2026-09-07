import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.models.agent_action import AgentAction
from app.models.task import Task
from app.models.user import User
from app.services.api_key_service import create_api_key
from tests.conftest import CsrfHeaders, TestSessionLocal


async def _api_key(test_user: User) -> str:
    async with TestSessionLocal() as session:
        created = await create_api_key(
            session,
            owner_id=test_user.id,
            name="Telegram agent",
            scopes=["tasks:read", "tasks:write", "notes:read", "notes:write"],
        )
        await session.commit()
        return created.plaintext_key


async def _login(
    client: AsyncClient, csrf_headers: CsrfHeaders, email: str, password: str
) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login", json={"email": email, "password": password}, headers=headers
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def test_api_key_mutation_requires_reasoning(client: AsyncClient, test_user: User) -> None:
    key = await _api_key(test_user)
    response = await client.post(
        "/tasks",
        json={"title": "Bez odůvodnění"},
        headers={"X-API-Key": key},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "agent_reasoning_required"


async def test_api_key_create_and_update_are_logged_with_before_and_batch(
    client: AsyncClient, test_user: User
) -> None:
    key = await _api_key(test_user)
    agent_headers = {
        "X-API-Key": key,
        "X-Agent-Reasoning": "User voice note requested fence check.",
        "X-Agent-Source": "telegram",
        "X-Agent-Source-System": "telegram_voice",
        "X-Agent-Batch-Id": "voice-123",
    }
    created = await client.post(
        "/tasks", json={"title": "Zkontrolovat plot"}, headers=agent_headers
    )
    assert created.status_code == 201
    task = created.json()
    assert task["created_by"] == "agent"
    assert task["api_key_id"] is not None

    updated = await client.patch(
        f"/tasks/{task['id']}",
        json={"title": "Zkontrolovat severní plot"},
        headers={**agent_headers, "If-Match": str(task["version"])},
    )
    assert updated.status_code == 200

    async with TestSessionLocal() as session:
        actions = (
            (await session.execute(select(AgentAction).order_by(AgentAction.created_at.asc())))
            .scalars()
            .all()
        )
    assert [action.action for action in actions] == ["create_task", "update_task"]
    assert actions[0].reasoning == "User voice note requested fence check."
    assert actions[0].source == "telegram"
    assert actions[0].source_system == "telegram_voice"
    assert actions[0].batch_id == "voice-123"
    assert actions[0].before_json is None
    assert actions[1].before_json is not None
    assert isinstance(actions[1].result_json, dict)
    assert actions[1].before_json["title"] == "Zkontrolovat plot"
    assert actions[1].result_json["title"] == "Zkontrolovat severní plot"


async def test_api_key_add_note_is_logged_and_visible_in_activity_filters(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    key = await _api_key(test_user)
    response = await client.post(
        "/notes",
        json={"title": "Agent note", "body": "summary", "kind": "note"},
        headers={
            "X-API-Key": key,
            "X-Agent-Reasoning": "User asked to remember summary.",
            "X-Agent-Source": "telegram",
            "X-Agent-Source-System": "telegram_text",
            "X-Agent-Batch-Id": "note-batch",
        },
    )
    assert response.status_code == 201
    note = response.json()
    assert note["created_by"] == "agent"

    csrf = await _login(client, csrf_headers, test_user.email, "correct-password")
    listed = await client.get(
        "/agent/actions",
        params={
            "action": "add_note",
            "source": "telegram",
            "source_system": "telegram_text",
            "entity_type": "note",
            "entity_id": note["id"],
            "only_unreverted": "true",
        },
        headers=csrf,
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["entity_type"] == "note"
    assert body["items"][0]["entity_id"] == note["id"]
    assert body["items"][0]["reasoning"] == "User asked to remember summary."


async def test_revert_batch_soft_deletes_created_tasks(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    key = await _api_key(test_user)
    headers = {
        "X-API-Key": key,
        "X-Agent-Reasoning": "Voice note produced multiple tasks.",
        "X-Agent-Batch-Id": "multi-task-batch",
    }
    first = await client.post("/tasks", json={"title": "Batch task 1"}, headers=headers)
    second = await client.post("/tasks", json={"title": "Batch task 2"}, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201

    csrf = await _login(client, csrf_headers, test_user.email, "correct-password")
    reverted = await client.post(
        "/agent/actions/revert-batch", json={"batch_id": "multi-task-batch"}, headers=csrf
    )
    assert reverted.status_code == 200
    assert len(reverted.json()["reverted_action_ids"]) == 2

    async with TestSessionLocal() as session:
        first_task = await session.get(Task, uuid.UUID(first.json()["id"]))
        second_task = await session.get(Task, uuid.UUID(second.json()["id"]))
        actions = (await session.execute(select(AgentAction))).scalars().all()
    assert first_task is not None
    assert second_task is not None
    assert first_task.deleted_at is not None
    assert second_task.deleted_at is not None
    assert any(action.action == "revert_batch" for action in actions)
    reverted_creates = [action for action in actions if action.action == "create_task"]
    assert all(action.reverted_at is not None for action in reverted_creates)


async def test_revert_update_restores_before_json_and_logs_revert(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    key = await _api_key(test_user)
    agent_headers = {
        "X-API-Key": key,
        "X-Agent-Reasoning": "User asked to rename task.",
        "X-Agent-Batch-Id": "batch-revert",
    }
    created = await client.post("/tasks", json={"title": "Původní"}, headers=agent_headers)
    task = created.json()
    updated = await client.patch(
        f"/tasks/{task['id']}",
        json={"title": "Agentí změna"},
        headers={**agent_headers, "If-Match": str(task["version"])},
    )
    assert updated.status_code == 200
    async with TestSessionLocal() as session:
        update_action = (
            await session.execute(select(AgentAction).where(AgentAction.action == "update_task"))
        ).scalar_one()

    csrf = await _login(client, csrf_headers, test_user.email, "correct-password")
    reverted = await client.post(f"/agent/actions/{update_action.id}/revert", headers=csrf)
    assert reverted.status_code == 200

    fetched = await client.get(f"/tasks/{task['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Původní"
    async with TestSessionLocal() as session:
        count = len((await session.execute(select(AgentAction))).scalars().all())
    assert count == 3


async def test_revert_detects_user_edit_conflict(
    client: AsyncClient, test_user: User, csrf_headers: CsrfHeaders
) -> None:
    key = await _api_key(test_user)
    agent_headers = {"X-API-Key": key, "X-Agent-Reasoning": "Automatic Telegram update."}
    created = await client.post("/tasks", json={"title": "Původní"}, headers=agent_headers)
    task = created.json()
    updated = await client.patch(
        f"/tasks/{task['id']}",
        json={"title": "Agentí změna"},
        headers={**agent_headers, "If-Match": str(task["version"])},
    )
    assert updated.status_code == 200
    async with TestSessionLocal() as session:
        update_action = (
            await session.execute(select(AgentAction).where(AgentAction.action == "update_task"))
        ).scalar_one()
        entity = await session.get(Task, uuid.UUID(task["id"]))
        assert entity is not None
        entity.title = "Ruční změna"
        entity.version += 1
        entity.updated_by = "user"
        await session.commit()

    csrf = await _login(client, csrf_headers, test_user.email, "correct-password")
    response = await client.post(f"/agent/actions/{update_action.id}/revert", headers=csrf)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "revert_conflict"
    assert detail["before_json"]["title"] == "Původní"
    assert detail["current_state"]["title"] == "Ruční změna"
