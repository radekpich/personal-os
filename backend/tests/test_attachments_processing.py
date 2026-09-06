import io
import os
import uuid
from pathlib import Path

from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select

from app.core.config import get_settings
from app.models.attachment import Attachment
from app.models.user import User
from tests.conftest import CsrfHeaders, TestSessionLocal


def _jpeg_bytes(width: int = 2600, height: int = 1200) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), "red")
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def _minimal_pdf() -> bytes:
    # One blank-ish PDF page generated as static bytes; pypdfium2 can render it.
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \ntrailer<</Root 1 0 R/Size 4>>\nstartxref\n181\n%%EOF\n"
    )


async def _login(client: AsyncClient, csrf_headers: CsrfHeaders, user: User) -> dict[str, str]:
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/login",
        json={"email": user.email, "password": "correct-password"},
        headers=headers,
    )
    assert response.status_code == 200
    return await csrf_headers(client)


async def _attachment_by_id(attachment_id: str) -> Attachment:
    async with TestSessionLocal() as session:
        attachment = (
            await session.execute(
                select(Attachment).where(Attachment.id == uuid.UUID(attachment_id))
            )
        ).scalar_one()
        return attachment


async def test_image_upload_is_normalized_to_jpeg_and_gets_thumbnail(
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
        files={"file": ("large.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["processing_status"] == "pending"
    attachment = await _attachment_by_id(response.json()["id"])
    assert attachment.processing_status == "ready"
    assert attachment.mime_type == "image/jpeg"
    assert attachment.width == 2000
    assert attachment.height == 923
    assert attachment.thumbnail_path is not None
    assert Path(attachment.storage_path).suffix == ".jpg"
    assert Path(attachment.thumbnail_path).exists()
    with Image.open(attachment.storage_path) as image:
        assert max(image.size) == 2000
        assert not image.getexif()
    with Image.open(attachment.thumbnail_path) as thumb:
        assert max(thumb.size) == 400
    get_settings.cache_clear()


async def test_pdf_upload_keeps_original_and_generates_first_page_thumbnail(
    client: AsyncClient,
    test_user: User,
    csrf_headers: CsrfHeaders,
    tmp_path: Path,
) -> None:
    os.environ["ATTACHMENTS_DIR"] = str(tmp_path)
    get_settings.cache_clear()
    headers = await _login(client, csrf_headers, test_user)
    pdf_bytes = _minimal_pdf()

    response = await client.post(
        "/attachments",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )

    assert response.status_code == 201
    attachment = await _attachment_by_id(response.json()["id"])
    assert attachment.processing_status == "ready"
    assert attachment.mime_type == "application/pdf"
    assert Path(attachment.storage_path).read_bytes() == pdf_bytes
    assert attachment.thumbnail_path is not None
    assert Path(attachment.thumbnail_path).exists()
    with Image.open(attachment.thumbnail_path) as thumb:
        assert thumb.format == "JPEG"
        assert max(thumb.size) <= 400
    get_settings.cache_clear()
