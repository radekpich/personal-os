import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.base import Base


def test_attachment_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTACHMENTS_DIR", raising=False)
    monkeypatch.delenv("MAX_ATTACHMENT_SIZE_MB", raising=False)
    monkeypatch.delenv("MAX_STORAGE_MB", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.attachments_dir == "./data/attachments"
    assert settings.max_attachment_size_mb == 15
    assert settings.max_storage_mb == 17_000
    assert settings.max_attachment_size_bytes == 15 * 1024 * 1024
    assert settings.max_storage_bytes == 17_000 * 1024 * 1024

    get_settings.cache_clear()


async def test_attachment_models_register_tables_and_columns() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        tables = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
        attachment_columns = await conn.run_sync(
            lambda sync_conn: {col["name"] for col in inspect(sync_conn).get_columns("attachments")}
        )
        task_attachment_columns = await conn.run_sync(
            lambda sync_conn: {
                col["name"] for col in inspect(sync_conn).get_columns("task_attachments")
            }
        )
        note_attachment_columns = await conn.run_sync(
            lambda sync_conn: {
                col["name"] for col in inspect(sync_conn).get_columns("note_attachments")
            }
        )
    await engine.dispose()

    assert {"attachments", "task_attachments", "note_attachments"}.issubset(tables)
    assert {
        "id",
        "owner_id",
        "storage_path",
        "thumbnail_path",
        "original_filename",
        "mime_type",
        "size_bytes",
        "width",
        "height",
        "checksum_sha256",
        "captured_at",
        "gps_lat",
        "gps_lon",
        "caption",
        "processing_status",
        "created_at",
        "deleted_at",
    }.issubset(attachment_columns)
    assert {"task_id", "attachment_id", "position"}.issubset(task_attachment_columns)
    assert {"note_id", "attachment_id", "position"}.issubset(note_attachment_columns)


def test_fresh_alembic_upgrade_creates_attachment_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "attachments.db"
    env = os.environ | {
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
        "SECRET_KEY": "test",
        "CORS_ORIGINS": "http://localhost",
        "COOKIE_SECURE": "false",
        "ENVIRONMENT": "test",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "REFRESH_TOKEN_EXPIRE_DAYS": "30",
        "ACCESS_COOKIE_NAME": "access_token",
        "REFRESH_COOKIE_NAME": "refresh_token",
        "CSRF_COOKIE_NAME": "csrf_token",
        "CSRF_HEADER_NAME": "X-CSRF-Token",
        "RATE_LIMIT_LOGIN": "5/minute",
        "RATE_LIMIT_DEFAULT": "100/minute",
    }

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0] for row in conn.execute("select name from sqlite_master where type='table'")
        }

    assert {"attachments", "task_attachments", "note_attachments"}.issubset(tables)
