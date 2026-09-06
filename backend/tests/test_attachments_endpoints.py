import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.models.attachment import Attachment, TaskAttachment
from app.models.task import Task
from app.models.user import User
from app.services.attachment_service import cleanup_deleted_and_orphaned_files
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
    client: AsyncClient, csrf_headers: CsrfHeaders, user: User, tmp_path: Path
) -> dict[str, object]:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, user)
    response = await client.post(
        "/attachments",
        files={"file": ("photo.jpg", _jpeg_bytes(800, 600), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


async def _create_task(owner: User) -> Task:
    async with TestSessionLocal() as session:
        task = Task(owner_id=owner.id, title="Úkol s přílohou")
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def test_attachment_thumb_patch_and_soft_delete(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    payload = await _upload_image(client, csrf_headers, test_user, tmp_path)
    attachment_id = payload["id"]
    headers = await csrf_headers(client)

    thumb = await client.get(f"/attachments/{attachment_id}/thumb")
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/jpeg"

    patched = await client.patch(
        f"/attachments/{attachment_id}", json={"caption": "Nový popisek"}, headers=headers
    )
    assert patched.status_code == 200
    assert patched.json()["caption"] == "Nový popisek"

    async with TestSessionLocal() as session:
        attachment = await session.get(Attachment, uuid.UUID(str(attachment_id)))
        assert attachment is not None
        storage_path = Path(attachment.storage_path)
        thumb_path = Path(attachment.thumbnail_path or "")

    deleted = await client.delete(f"/attachments/{attachment_id}", headers=headers)
    assert deleted.status_code == 204
    assert storage_path.exists()
    assert thumb_path.exists()
    assert (await client.get(f"/attachments/{attachment_id}")).status_code == 404
    assert (await client.get(f"/attachments/{attachment_id}/thumb")).status_code == 404
    get_settings.cache_clear()


async def test_task_attachment_link_and_unlink(
    client: AsyncClient,
    test_user: User,
    other_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    payload = await _upload_image(client, csrf_headers, test_user, tmp_path)
    attachment_id = payload["id"]
    task = await _create_task(test_user)
    foreign_task = await _create_task(other_user)
    headers = await csrf_headers(client)

    linked = await client.post(
        f"/tasks/{task.id}/attachments",
        json={"attachment_id": attachment_id, "position": 2},
        headers=headers,
    )
    assert linked.status_code == 201
    assert linked.json()["attachment_id"] == attachment_id
    assert linked.json()["position"] == 2

    foreign = await client.post(
        f"/tasks/{foreign_task.id}/attachments",
        json={"attachment_id": attachment_id, "position": 0},
        headers=headers,
    )
    assert foreign.status_code == 404

    async with TestSessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(TaskAttachment).where(
                        TaskAttachment.attachment_id == uuid.UUID(str(attachment_id))
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1

    unlinked = await client.delete(f"/tasks/{task.id}/attachments/{attachment_id}", headers=headers)
    assert unlinked.status_code == 204
    async with TestSessionLocal() as session:
        remaining = (
            (
                await session.execute(
                    select(TaskAttachment).where(
                        TaskAttachment.attachment_id == uuid.UUID(str(attachment_id))
                    )
                )
            )
            .scalars()
            .all()
        )
        assert remaining == []
    get_settings.cache_clear()


async def test_cleanup_removes_old_deleted_and_orphan_files(
    tmp_path: Path, test_user: User
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    old_file = tmp_path / str(test_user.id) / "2026" / "09" / "old.jpg"
    old_thumb = tmp_path / str(test_user.id) / "2026" / "09" / "old_thumb.jpg"
    old_file.parent.mkdir(parents=True)
    old_file.write_bytes(b"old")
    old_thumb.write_bytes(b"thumb")
    orphan = tmp_path / str(test_user.id) / "2026" / "09" / "orphan.jpg"
    orphan.write_bytes(b"orphan")

    async with TestSessionLocal() as session:
        attachment = Attachment(
            owner_id=test_user.id,
            storage_path=str(old_file),
            thumbnail_path=str(old_thumb),
            original_filename="old.jpg",
            mime_type="image/jpeg",
            size_bytes=3,
            checksum_sha256="a" * 64,
            processing_status="ready",
            deleted_at=datetime.now(UTC) - timedelta(days=31),
        )
        session.add(attachment)
        await session.commit()

    result = await cleanup_deleted_and_orphaned_files(TestSessionLocal, get_settings())

    assert result["deleted_database_files"] == 2
    assert result["deleted_orphan_files"] == 1
    assert not old_file.exists()
    assert not old_thumb.exists()
    assert not orphan.exists()
    get_settings.cache_clear()
