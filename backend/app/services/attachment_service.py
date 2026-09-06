import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.attachment import Attachment, AttachmentProcessingStatus
from app.models.user import User

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
