from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user import User

VTIMEZONE_EUROPE_PRAGUE = """BEGIN:VTIMEZONE\r
TZID:Europe/Prague\r
X-LIC-LOCATION:Europe/Prague\r
BEGIN:DAYLIGHT\r
TZOFFSETFROM:+0100\r
TZOFFSETTO:+0200\r
TZNAME:CEST\r
DTSTART:19700329T020000\r
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU\r
END:DAYLIGHT\r
BEGIN:STANDARD\r
TZOFFSETFROM:+0200\r
TZOFFSETTO:+0100\r
TZNAME:CET\r
DTSTART:19701025T030000\r
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU\r
END:STANDARD\r
END:VTIMEZONE"""


def _escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _format_date(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%SZ")


def _format_local_datetime(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _format_all_day(value: date) -> str:
    return value.strftime("%Y%m%d")


def _event_lines(task: Task, generated_at: datetime) -> list[str]:
    assert task.due_date is not None
    lines = [
        "BEGIN:VEVENT",
        f"UID:task-{task.id}@personal-os",
        f"DTSTAMP:{_format_date(generated_at)}",
        f"SUMMARY:{_escape_ics_text(task.title)}",
    ]
    if task.due_time is None:
        lines.append(f"DTSTART;VALUE=DATE:{_format_all_day(task.due_date)}")
    else:
        start = datetime.combine(task.due_date, task.due_time)
        duration = timedelta(minutes=task.estimate_minutes or 30)
        end = start + duration
        lines.append(f"DTSTART;TZID=Europe/Prague:{_format_local_datetime(start)}")
        lines.append(f"DTEND;TZID=Europe/Prague:{_format_local_datetime(end)}")
    if task.recurrence_rule:
        lines.append(f"RRULE:{task.recurrence_rule}")
    lines.append("END:VEVENT")
    return lines


async def get_user_by_calendar_token(db: AsyncSession, token: str) -> User | None:
    result = await db.execute(
        select(User).where(User.calendar_token == token, User.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def render_calendar_for_user(db: AsyncSession, user: User) -> str:
    result = await db.execute(
        select(Task)
        .where(Task.owner_id == user.id, Task.deleted_at.is_(None), Task.due_date.is_not(None))
        .order_by(Task.due_date, Task.due_time, Task.position, Task.created_at)
    )
    tasks = list(result.scalars().all())
    generated_at = datetime.utcnow()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Personal OS//Tasks Calendar//CS",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        VTIMEZONE_EUROPE_PRAGUE,
    ]
    for task in tasks:
        lines.extend(_event_lines(task, generated_at))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
