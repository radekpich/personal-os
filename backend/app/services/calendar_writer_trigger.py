import asyncio
import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


async def trigger_calendar_writer(settings: Settings) -> None:
    """Run the configured calendar writer trigger without blocking the API response.

    The trigger is intentionally best-effort: Personal OS stores the durable
    CalendarRequest first, then this hook nudges the external writer to process
    it immediately. A cron fallback can still pick up pending rows if the trigger
    command is missing or fails.
    """
    command = (settings.calendar_writer_trigger_command or "").strip()
    if not command:
        return
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
    except Exception:
        logger.exception("calendar writer trigger failed to start")
        return
    if process.returncode != 0:
        logger.warning(
            "calendar writer trigger exited with %s: stdout=%s stderr=%s",
            process.returncode,
            stdout.decode("utf-8", errors="replace")[:2000],
            stderr.decode("utf-8", errors="replace")[:2000],
        )
