import os
import uuid
from pathlib import Path
from typing import Any, cast

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.models.attachment import NoteAttachment
from app.models.note import Note
from app.models.user import User
from tests.conftest import CsrfHeaders, TestSessionLocal
from tests.test_attachments_processing import _jpeg_bytes


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, user: User) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def _upload_image(
    client: AsyncClient,
    csrf_headers: CsrfHeaders,
    user: User,
    tmp_path: Path,
    name: str,
    width: int = 640,
) -> dict[str, Any]:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, user)
    response = await client.post(
        "/attachments",
        files={"file": (name, _jpeg_bytes(width, 480), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


async def _create_note(owner: User, title: str = "Deník s fotkami") -> Note:
    async with TestSessionLocal() as session:
        note = Note(owner_id=owner.id, title=title, body="text", kind="diary")
        session.add(note)
        await session.commit()
        await session.refresh(note)
        return note


async def test_note_attachment_link_list_and_unlink(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    first = await _upload_image(client, csrf_headers, test_user, tmp_path, "first.jpg")
    second = await _upload_image(client, csrf_headers, test_user, tmp_path, "second.jpg", 800)
    note = await _create_note(test_user)
    headers = await csrf_headers(client)

    linked_second = await client.post(
        f"/notes/{note.id}/attachments",
        json={"attachment_id": second["id"], "position": 20},
        headers=headers,
    )
    linked_first = await client.post(
        f"/notes/{note.id}/attachments",
        json={"attachment_id": first["id"], "position": 10},
        headers=headers,
    )

    assert linked_second.status_code == 201
    assert linked_second.json()["note_id"] == str(note.id)
    assert linked_second.json()["attachment_id"] == second["id"]
    assert linked_first.status_code == 201

    listed = await client.get(f"/notes/{note.id}/attachments")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [first["id"], second["id"]]

    relinked = await client.post(
        f"/notes/{note.id}/attachments",
        json={"attachment_id": first["id"], "position": 30},
        headers=headers,
    )
    assert relinked.status_code == 201
    assert relinked.json()["position"] == 30

    reordered = await client.get(f"/notes/{note.id}/attachments")
    assert [item["id"] for item in reordered.json()["items"]] == [second["id"], first["id"]]

    unlinked = await client.delete(f"/notes/{note.id}/attachments/{first['id']}", headers=headers)
    assert unlinked.status_code == 204

    async with TestSessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(NoteAttachment).where(
                        NoteAttachment.attachment_id == uuid.UUID(str(first["id"]))
                    )
                )
            )
            .scalars()
            .all()
        )
        assert rows == []
    get_settings.cache_clear()


async def test_note_attachment_masks_foreign_note_and_attachment(
    client: AsyncClient,
    test_user: User,
    other_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    own_attachment = await _upload_image(client, csrf_headers, test_user, tmp_path, "own.jpg")
    foreign_attachment = await _upload_image(
        client, csrf_headers, other_user, tmp_path, "foreign.jpg", 800
    )
    own_note = await _create_note(test_user, "Moje")
    foreign_note = await _create_note(other_user, "Cizí")
    headers = await _login(client, csrf_headers, test_user)

    foreign_note_response = await client.post(
        f"/notes/{foreign_note.id}/attachments",
        json={"attachment_id": own_attachment["id"]},
        headers=headers,
    )
    assert foreign_note_response.status_code == 404

    foreign_attachment_response = await client.post(
        f"/notes/{own_note.id}/attachments",
        json={"attachment_id": foreign_attachment["id"]},
        headers=headers,
    )
    assert foreign_attachment_response.status_code == 404
    assert (await client.get(f"/notes/{foreign_note.id}/attachments")).status_code == 404
    assert (
        await client.delete(
            f"/notes/{own_note.id}/attachments/{foreign_attachment['id']}", headers=headers
        )
    ).status_code == 404
    get_settings.cache_clear()
