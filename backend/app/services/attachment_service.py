import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.attachment import Attachment, AttachmentProcessingStatus
from app.models.user import User

try:
    from pillow_heif import register_heif_opener  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - optional import guard for broken deployments
    register_heif_opener = None

CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class DetectedFileType:
    mime_type: str
    extension: str


ALLOWED_SIGNATURES = (
    (b"\xff\xd8\xff", DetectedFileType("image/jpeg", "jpg")),
    (b"\x89PNG\r\n\x1a\n", DetectedFileType("image/png", "png")),
    (b"RIFF", DetectedFileType("image/webp", "webp")),
    (b"%PDF-", DetectedFileType("application/pdf", "pdf")),
)


def sanitize_filename(filename: str) -> str:
    cleaned = filename.replace("\\", "_").replace("/", "_").strip()
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:255] or "upload"


def detect_file_type(header: bytes) -> DetectedFileType:
    if len(header) >= 12 and header[4:12] in {b"ftypheic", b"ftypheix", b"ftyphevc", b"ftyphevx"}:
        return DetectedFileType("image/heic", "heic")
    if len(header) >= 12 and header[4:12] in {b"ftypmif1", b"ftypmsf1"}:
        return DetectedFileType("image/heic", "heic")
    for signature, file_type in ALLOWED_SIGNATURES:
        if header.startswith(signature):
            if file_type.mime_type == "image/webp" and header[8:12] != b"WEBP":
                break
            return file_type
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")


def build_storage_path(
    settings: Settings, owner_id: uuid.UUID, attachment_id: uuid.UUID, ext: str
) -> Path:
    now = datetime.now(UTC)
    return (
        Path(settings.attachments_dir)
        / str(owner_id)
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{attachment_id}.{ext}"
    )


async def storage_usage(
    db: AsyncSession, owner: User, settings: Settings
) -> tuple[int, int, int, int, float]:
    stmt = select(
        func.count(Attachment.id), func.coalesce(func.sum(Attachment.size_bytes), 0)
    ).where(
        Attachment.owner_id == owner.id,
        Attachment.deleted_at.is_(None),
    )
    count, used = (await db.execute(stmt)).one()
    used_bytes = int(used or 0)
    max_bytes = settings.max_storage_bytes
    remaining = max(max_bytes - used_bytes, 0)
    percent = round((used_bytes / max_bytes) * 100, 2) if max_bytes > 0 else 100.0
    return int(count), used_bytes, max_bytes, remaining, percent


def _remove_empty_parents(path: Path, stop_at: Path) -> None:
    current = path.parent
    stop_at = stop_at.resolve()
    while current.exists() and current.resolve() != stop_at:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _parse_exif_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def _ratio_to_float(value: Any) -> float:
    if isinstance(value, tuple) and len(value) == 2:
        numerator, denominator = value
        return float(numerator) / float(denominator)
    return float(value)


def _gps_coord(values: Any, ref: Any) -> float | None:
    if not isinstance(values, tuple | list) or len(values) != 3:
        return None
    degrees = _ratio_to_float(values[0])
    minutes = _ratio_to_float(values[1])
    seconds = _ratio_to_float(values[2])
    coordinate = degrees + minutes / 60 + seconds / 3600
    if ref in {"S", "W", b"S", b"W"}:
        coordinate *= -1
    return coordinate


def _extract_image_metadata(
    image: Image.Image,
) -> tuple[datetime | None, float | None, float | None]:
    exif = image.getexif()
    captured_at = _parse_exif_datetime(exif.get(36867))
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_ifd = exif.get_ifd(34853) if exif else {}
    if gps_ifd:
        gps_lat = _gps_coord(gps_ifd.get(2), gps_ifd.get(1))
        gps_lon = _gps_coord(gps_ifd.get(4), gps_ifd.get(3))
    return captured_at, gps_lat, gps_lon


def _thumbnail_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_thumb.jpg")


def _save_jpeg(image: Image.Image, path: Path, max_edge: int, quality: int = 85) -> tuple[int, int]:
    normalized = image.convert("RGB")
    normalized.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    normalized.save(path, format="JPEG", quality=quality, optimize=True)
    return normalized.size


def _process_image(attachment: Attachment) -> dict[str, Any]:
    if register_heif_opener is not None:
        register_heif_opener()
    source_path = Path(attachment.storage_path)
    with Image.open(source_path) as opened:
        captured_at, gps_lat, gps_lon = _extract_image_metadata(opened)
        image = cast(Image.Image, ImageOps.exif_transpose(opened))
        final_path = source_path.with_suffix(".jpg")
        temp_path = final_path.with_suffix(".processing.jpg")
        width, height = _save_jpeg(image, temp_path, max_edge=2000)
        os.replace(temp_path, final_path)
        if final_path != source_path:
            source_path.unlink(missing_ok=True)
        thumb_path = _thumbnail_path(final_path)
        thumb_temp_path = thumb_path.with_suffix(".processing.jpg")
        _save_jpeg(image, thumb_temp_path, max_edge=400)
        os.replace(thumb_temp_path, thumb_path)
    return {
        "storage_path": str(final_path),
        "thumbnail_path": str(thumb_path),
        "mime_type": "image/jpeg",
        "size_bytes": final_path.stat().st_size,
        "width": width,
        "height": height,
        "captured_at": captured_at,
        "gps_lat": gps_lat,
        "gps_lon": gps_lon,
    }


def _process_pdf(attachment: Attachment) -> dict[str, Any]:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    source_path = Path(attachment.storage_path)
    thumb_path = _thumbnail_path(source_path)
    pdf = pdfium.PdfDocument(str(source_path))
    try:
        page = pdf[0]
        try:
            bitmap = page.render(scale=2)
            image = bitmap.to_pil()
            _save_jpeg(image, thumb_path, max_edge=400)
        finally:
            page.close()
    finally:
        pdf.close()
    return {
        "thumbnail_path": str(thumb_path),
        "size_bytes": source_path.stat().st_size,
    }


async def process_attachment_in_session(db: AsyncSession, attachment_id: uuid.UUID) -> None:
    attachment = await db.get(Attachment, attachment_id)
    if attachment is None or attachment.deleted_at is not None:
        return
    try:
        if attachment.mime_type.startswith("image/"):
            updates = _process_image(attachment)
        elif attachment.mime_type == "application/pdf":
            updates = _process_pdf(attachment)
        else:
            updates = {}
        for key, value in updates.items():
            setattr(attachment, key, value)
        attachment.processing_status = AttachmentProcessingStatus.READY.value
    except Exception:
        attachment.processing_status = AttachmentProcessingStatus.FAILED.value
    await db.commit()


async def upload_attachment(
    db: AsyncSession,
    owner: User,
    settings: Settings,
    file: UploadFile,
    caption: str | None,
) -> tuple[Attachment, bool]:
    original_filename = sanitize_filename(file.filename or "upload")
    temp_dir = Path(settings.attachments_dir) / ".tmp" / str(owner.id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}.upload"
    hasher = hashlib.sha256()
    size = 0
    detected: DetectedFileType | None = None
    header = b""

    try:
        with temp_path.open("wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_attachment_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Uploaded file exceeds {settings.max_attachment_size_mb} MB limit",
                    )
                if detected is None:
                    header = (header + chunk)[:32]
                    if len(header) >= 12 or size == len(chunk):
                        detected = detect_file_type(header)
                hasher.update(chunk)
                output.write(chunk)
        if detected is None:
            detected = detect_file_type(header)

        _, used_bytes, max_bytes, _, _ = await storage_usage(db, owner, settings)
        if used_bytes + size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                detail="Storage limit exceeded; delete old attachments or raise MAX_STORAGE_MB",
            )

        checksum = hasher.hexdigest()
        existing = (
            await db.execute(
                select(Attachment).where(
                    Attachment.owner_id == owner.id,
                    Attachment.checksum_sha256 == checksum,
                    Attachment.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            temp_path.unlink(missing_ok=True)
            _remove_empty_parents(temp_path, Path(settings.attachments_dir))
            return existing, False

        attachment_id = uuid.uuid4()
        final_path = build_storage_path(settings, owner.id, attachment_id, detected.extension)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temp_path, final_path)
        attachment = Attachment(
            id=attachment_id,
            owner_id=owner.id,
            storage_path=str(final_path),
            thumbnail_path=None,
            original_filename=original_filename,
            mime_type=detected.mime_type,
            size_bytes=size,
            checksum_sha256=checksum,
            caption=caption,
            processing_status=AttachmentProcessingStatus.PENDING.value,
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment, True
    except Exception:
        temp_path.unlink(missing_ok=True)
        _remove_empty_parents(temp_path, Path(settings.attachments_dir))
        raise


async def get_owned_attachment(
    db: AsyncSession, owner: User, attachment_id: uuid.UUID
) -> Attachment:
    attachment = (
        await db.execute(
            select(Attachment).where(
                Attachment.id == attachment_id,
                Attachment.owner_id == owner.id,
                Attachment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="attachment not found")
    return attachment
