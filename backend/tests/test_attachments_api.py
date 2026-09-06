import os
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.models.attachment import Attachment
from app.models.user import User
from tests.conftest import CsrfHeaders, TestSessionLocal

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"JFIF\x00" + b"\x00" * 64
PDF_BYTES = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"0" * 64


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, user: User) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def test_upload_allowed_file_uses_magic_bytes_and_server_generated_path(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, test_user)

    response = await client.post(
        "/attachments",
        files={"file": ("../../evil.php", PNG_BYTES, "application/x-php")},
        data={"caption": "Účtenka"},
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert "/" not in payload["original_filename"]
    assert "\\" not in payload["original_filename"]
    assert payload["original_filename"].endswith("evil.php")
    assert payload["mime_type"] == "image/png"
    assert payload["size_bytes"] == len(PNG_BYTES)
    assert payload["processing_status"] == "pending"
    assert payload["caption"] == "Účtenka"
    assert str(test_user.id) in payload["storage_path"]
    assert "evil" not in Path(payload["storage_path"]).name
    assert Path(payload["storage_path"]).exists()
    assert Path(payload["storage_path"]).is_relative_to(tmp_path)

    usage = await client.get("/storage/usage")
    assert usage.status_code == 200
    assert usage.json()["file_count"] == 1
    assert usage.json()["used_bytes"] == len(PNG_BYTES)

    get_settings.cache_clear()


async def test_upload_rejects_forbidden_magic_type(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, test_user)

    response = await client.post(
        "/attachments",
        files={"file": ("note.txt", b"hello", "image/png")},
        headers=headers,
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
    assert not list(tmp_path.rglob("*"))
    get_settings.cache_clear()


async def test_upload_enforces_per_file_size_limit_while_streaming(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    os.environ["MAX_ATTACHMENT_SIZE_MB"] = "0"
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, test_user)

    response = await client.post(
        "/attachments",
        files={"file": ("tiny.jpg", JPEG_BYTES, "image/jpeg")},
        headers=headers,
    )

    assert response.status_code == 413
    assert "exceeds 0 MB" in response.json()["detail"]
    assert not list(tmp_path.rglob("*"))
    os.environ.pop("MAX_ATTACHMENT_SIZE_MB")
    get_settings.cache_clear()


async def test_upload_enforces_total_storage_limit(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    os.environ["MAX_STORAGE_MB"] = "0"
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, test_user)

    response = await client.post(
        "/attachments",
        files={"file": ("tiny.pdf", PDF_BYTES, "application/pdf")},
        headers=headers,
    )

    assert response.status_code == 507
    assert "Storage limit exceeded" in response.json()["detail"]
    assert not list(tmp_path.rglob("*"))
    os.environ.pop("MAX_STORAGE_MB")
    get_settings.cache_clear()


async def test_foreign_attachment_returns_404(
    client: AsyncClient,
    test_user: User,
    other_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, test_user)
    created = await client.post(
        "/attachments",
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
        headers=headers,
    )
    assert created.status_code == 201

    other_headers = await _login(client, csrf_headers, other_user)
    response = await client.get(f"/attachments/{created.json()['id']}", headers=other_headers)

    assert response.status_code == 404
    get_settings.cache_clear()


async def test_duplicate_upload_reuses_existing_physical_file(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, test_user)

    first = await client.post(
        "/attachments", files={"file": ("first.png", PNG_BYTES, "image/png")}, headers=headers
    )
    second = await client.post(
        "/attachments", files={"file": ("second.png", PNG_BYTES, "image/png")}, headers=headers
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["storage_path"] == first.json()["storage_path"]
    async with TestSessionLocal() as session:
        attachments = (await session.execute(select(Attachment))).scalars().all()
    assert len(attachments) == 1
    assert len([path for path in tmp_path.rglob("*") if path.is_file()]) == 1
    get_settings.cache_clear()
