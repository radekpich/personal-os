from sqlalchemy import select

from app.models.user import User
from tests.conftest import TestSessionLocal


async def test_new_user_gets_unique_calendar_token() -> None:
    async with TestSessionLocal() as session:
        first = User(
            email="calendar-one@example.com",
            hashed_password="hashed-password",
            display_name="Calendar One",
        )
        second = User(
            email="calendar-two@example.com",
            hashed_password="hashed-password",
            display_name="Calendar Two",
        )
        session.add_all([first, second])
        await session.commit()
        await session.refresh(first)
        await session.refresh(second)

        assert first.calendar_token
        assert second.calendar_token
        assert first.calendar_token != second.calendar_token
        assert len(first.calendar_token) >= 32

        result = await session.execute(
            select(User).where(User.calendar_token == first.calendar_token)
        )
        assert result.scalar_one().id == first.id
