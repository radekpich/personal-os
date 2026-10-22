"""Seed only an isolated calendar-smoke DB; never production or a real calendar.

From backend/, after sourcing required test config, override DATABASE_URL to a
fresh path containing `calendar-smoke` and CALENDAR_WRITER_TRIGGER_COMMAND="".
Run Alembic upgrade head, then:
  PYTHONPATH=. .venv/bin/python ../frontend/scripts/calendar-smoke-setup.py
Start backend at 127.0.0.1:8031. The JS date-sync smoke routes all browser API
requests to that backend; the live production DB and Google are not used.
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.external_calendar import ExternalCalendar
from app.models.user import User


async def main() -> None:
    settings = get_settings()
    assert "calendar-smoke" in str(settings.database_url), "Not a smoke database"
    assert not settings.calendar_writer_trigger_command, "Disable Google writer first"
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(
                select(User).where(User.email == "calendar-smoke@example.test")
            )
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email="calendar-smoke@example.test",
                display_name="Calendar smoke",
                hashed_password=hash_password("Calendar-smoke-only-2026"),
                timezone="Europe/Prague",
            )
            db.add(user)
            await db.flush()
        calendar = (
            (
                await db.execute(
                    select(ExternalCalendar).where(ExternalCalendar.owner_id == user.id)
                )
            )
            .scalars()
            .first()
        )
        if calendar is None:
            db.add(
                ExternalCalendar(
                    owner_id=user.id,
                    external_id="calendar-smoke-only",
                    name="Testovací kalendář",
                    can_write=True,
                    is_enabled=True,
                    is_default=True,
                    last_synced_at=datetime.now(UTC),
                )
            )
        category = (
            (await db.execute(select(Category).where(Category.owner_id == user.id)))
            .scalars()
            .first()
        )
        if category is None:
            db.add(Category(owner_id=user.id, name="Test", color="#123456", icon="dot"))
        await db.commit()
    print("Isolated calendar smoke DB ready; external writer disabled")


if __name__ == "__main__":
    asyncio.run(main())
