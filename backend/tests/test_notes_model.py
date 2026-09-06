import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
from app.models.note import NoteKind


async def test_note_models_register_tables_columns_and_foreign_keys() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        tables = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
        note_columns = await conn.run_sync(
            lambda sync_conn: {col["name"] for col in inspect(sync_conn).get_columns("notes")}
        )
        note_indexes = await conn.run_sync(
            lambda sync_conn: {idx["name"] for idx in inspect(sync_conn).get_indexes("notes")}
        )
        note_attachment_fks = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_foreign_keys("note_attachments")
        )
    await engine.dispose()

    assert NoteKind.DIARY.value == "diary"
    assert {"notes", "note_attachments"}.issubset(tables)
    assert {
        "id",
        "owner_id",
        "title",
        "body",
        "kind",
        "entry_date",
        "entry_time",
        "mood",
        "category_id",
        "vision_id",
        "task_id",
        "created_at",
        "updated_at",
        "deleted_at",
    }.issubset(note_columns)
    assert "ix_notes_owner_id" in note_indexes
    fk_targets = {
        (fk["constrained_columns"][0], fk["referred_table"]) for fk in note_attachment_fks
    }
    assert ("note_id", "notes") in fk_targets
    assert ("attachment_id", "attachments") in fk_targets


def test_fresh_alembic_upgrade_creates_notes_tables_and_fk(tmp_path: Path) -> None:
    db_path = tmp_path / "notes.db"
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
        note_columns = {row[1] for row in conn.execute("pragma table_info(notes)")}
        note_attachment_fks = {
            (row[3], row[2]) for row in conn.execute("pragma foreign_key_list(note_attachments)")
        }

    assert "notes" in tables
    assert {"kind", "entry_date", "entry_time", "mood", "task_id", "vision_id"}.issubset(
        note_columns
    )
    assert ("note_id", "notes") in note_attachment_fks
