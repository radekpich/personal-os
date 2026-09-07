from datetime import date

from httpx import AsyncClient

from app.models.category import Category
from app.models.note import Note
from app.models.task import Task
from app.models.user import User
from app.models.vision import Vision
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


async def _create_links(owner: User) -> tuple[str, str, str]:
    async with TestSessionLocal() as session:
        category = Category(owner_id=owner.id, name="Deník", color="#c084fc", icon="book")
        vision = Vision(owner_id=owner.id, title="Rodinné vzpomínky", horizon="1y")
        task = Task(owner_id=owner.id, title="Dopsat zápis", status="todo")
        session.add_all([category, vision, task])
        await session.commit()
        await session.refresh(category)
        await session.refresh(vision)
        await session.refresh(task)
        return str(category.id), str(vision.id), str(task.id)


async def test_notes_require_auth(client: AsyncClient) -> None:
    response = await client.get("/notes")

    assert response.status_code == 401


async def test_create_list_get_update_and_delete_note(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    category_id, vision_id, task_id = await _create_links(test_user)

    created = await client.post(
        "/notes",
        json={
            "title": "Nedělní zápis",
            "body": "## Deník\nByli jsme venku.",
            "kind": "diary",
            "entry_date": "2026-09-06",
            "entry_time": "18:30:00",
            "mood": "klid",
            "category_id": category_id,
            "vision_id": vision_id,
            "task_id": task_id,
        },
        headers=headers,
    )

    assert created.status_code == 201
    note = created.json()
    assert note["title"] == "Nedělní zápis"
    assert note["body"].startswith("## Deník")
    assert note["kind"] == "diary"
    assert note["entry_date"] == "2026-09-06"
    assert note["entry_time"] == "18:30:00"
    assert note["mood"] == "klid"
    assert note["category_id"] == category_id
    assert note["vision_id"] == vision_id
    assert note["task_id"] == task_id
    assert note["owner_id"] == str(test_user.id)

    await client.post(
        "/notes",
        json={"title": "Nápad", "body": "Média index", "kind": "idea"},
        headers=headers,
    )

    listed = await client.get("/notes", params={"kind": "diary", "q": "venku"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [note["id"]]
    assert listed.json()["total"] == 1

    by_day = await client.get("/notes", params={"entry_date": "2026-09-06"})
    assert [item["id"] for item in by_day.json()["items"]] == [note["id"]]

    fetched = await client.get(f"/notes/{note['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == note["id"]

    updated = await client.patch(
        f"/notes/{note['id']}",
        json={"title": "Upravený zápis", "mood": None, "task_id": None},
        headers={**headers, "If-Match": str(note["version"])},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Upravený zápis"
    assert updated.json()["mood"] is None
    assert updated.json()["task_id"] is None

    deleted = await client.delete(
        f"/notes/{note['id']}", headers={**headers, "If-Match": str(updated.json()["version"])}
    )
    assert deleted.status_code == 204
    assert (await client.get(f"/notes/{note['id']}")).status_code == 404
    remaining_ids = {item["id"] for item in (await client.get("/notes")).json()["items"]}
    assert note["id"] not in remaining_ids


async def test_note_rejects_foreign_links_and_masks_foreign_note(
    client: AsyncClient,
    test_user: User,
    other_user: User,
    csrf_headers: CsrfHeaders,
) -> None:
    headers = await _login(client, csrf_headers, test_user)
    other_category_id, other_vision_id, other_task_id = await _create_links(other_user)

    for payload in (
        {"title": "Cizí kategorie", "category_id": other_category_id},
        {"title": "Cizí vize", "vision_id": other_vision_id},
        {"title": "Cizí úkol", "task_id": other_task_id},
    ):
        response = await client.post("/notes", json=payload, headers=headers)
        assert response.status_code == 404

    async with TestSessionLocal() as session:
        foreign_note = Note(
            owner_id=other_user.id,
            title="Cizí poznámka",
            body="tajné",
            kind="note",
            entry_date=date(2026, 9, 6),
        )
        session.add(foreign_note)
        await session.commit()
        await session.refresh(foreign_note)
        foreign_note_id = str(foreign_note.id)

    assert (await client.get(f"/notes/{foreign_note_id}")).status_code == 404
    assert (
        await client.patch(
            f"/notes/{foreign_note_id}",
            json={"title": "x"},
            headers={**headers, "If-Match": "1"},
        )
    ).status_code == 404
    assert (
        await client.delete(f"/notes/{foreign_note_id}", headers={**headers, "If-Match": "1"})
    ).status_code == 404
