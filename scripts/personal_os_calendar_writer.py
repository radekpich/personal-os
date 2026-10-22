#!/usr/bin/env python3
"""Personal OS -> Google Calendar writer.

No-agent cron script. It keeps Personal OS' external calendar list in sync with
Google Calendar and processes pending CalendarRequest rows by claiming them via
Personal OS API, performing the Google Calendar mutation, and completing the
request back in Personal OS.

Stdout is intentionally empty on success/no work. Non-empty stdout means an
operator-visible warning/error.
"""

from __future__ import annotations

import json
from html import escape
import re
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE_URL = os.environ.get("PERSONAL_OS_BASE_URL", "http://38.79.154.155:8030").rstrip(
    "/"
)
API_KEY_PATH = Path(
    os.environ.get(
        "PERSONAL_OS_CALENDAR_WRITER_API_KEY_PATH",
        "/home/zeus/.hermes/secrets/personal_os_calendar_writer_api_key",
    )
)
GOOGLE_TOKEN_PATH = Path(
    os.environ.get("GOOGLE_TOKEN_PATH", "/home/zeus/.hermes/google_token.json")
)
STATE_PATH = Path(
    os.environ.get(
        "PERSONAL_OS_CALENDAR_WRITER_STATE",
        "/home/zeus/.hermes/state/personal_os_calendar_writer.json",
    )
)
TZ = ZoneInfo("Europe/Prague")
MAX_PER_RUN = int(os.environ.get("PERSONAL_OS_CALENDAR_WRITER_MAX_PER_RUN", "10"))
SYNC_INTERVAL_SECONDS = int(
    os.environ.get("PERSONAL_OS_CALENDAR_SYNC_INTERVAL_SECONDS", "3600")
)
TASK_URL_BASE = os.environ.get(
    "PERSONAL_OS_TASK_URL_BASE", "http://38.79.154.155:3030/tasks"
)


@dataclass
class RunStats:
    synced: bool = False
    processed: int = 0
    completed: int = 0
    failed: int = 0
    messages: list[str] | None = None

    def add(self, message: str) -> None:
        if self.messages is None:
            self.messages = []
        self.messages.append(message)


def api_key() -> str:
    return API_KEY_PATH.read_text(encoding="utf-8").strip()


def request_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={
            "X-API-Key": api_key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def calendar_service() -> Any:
    creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH))
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def google_calendars(service: Any) -> list[dict[str, Any]]:
    calendars: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        response = (
            service.calendarList()
            .list(pageToken=page_token, minAccessRole="reader")
            .execute()
        )
        for item in response.get("items", []):
            access = item.get("accessRole")
            calendars.append(
                {
                    "external_id": item["id"],
                    "name": item.get("summaryOverride")
                    or item.get("summary")
                    or item["id"],
                    "color": item.get("backgroundColor"),
                    "can_write": access in {"owner", "writer"},
                    "is_shared": not bool(item.get("primary")),
                    "is_primary": bool(item.get("primary")),
                    "is_enabled": access in {"owner", "writer"},
                    "is_default": bool(item.get("primary")),
                }
            )
        page_token = response.get("nextPageToken")
        if not page_token:
            return calendars


def sync_calendars_if_due(service: Any, stats: RunStats) -> None:
    state = load_state()
    now = datetime.now(UTC)
    last_raw = state.get("last_sync_at")
    try:
        last = datetime.fromisoformat(last_raw) if last_raw else None
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
    except Exception:
        last = None
    if last and (now - last).total_seconds() < SYNC_INTERVAL_SECONDS:
        return
    calendars = google_calendars(service)
    request_json(
        "/agent/calendars/sync", method="POST", payload={"calendars": calendars}
    )
    state["last_sync_at"] = now.isoformat()
    state["last_sync_count"] = len(calendars)
    save_state(state)
    stats.synced = True


def pending_requests() -> list[dict[str, Any]]:
    payload = request_json("/agent/calendar-requests?status=pending")
    return list(payload.get("items", []))


def claim(request_id: str) -> dict[str, Any] | None:
    try:
        return request_json(
            f"/agent/calendar-requests/{request_id}/claim", method="POST"
        )
    except urllib.error.HTTPError as exc:
        # 409 means another worker claimed it. That is fine.
        if exc.code == 409:
            return None
        raise


def complete(
    request_id: str,
    *,
    event_id: str | None,
    event_link: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    return request_json(
        f"/agent/calendar-requests/{request_id}/complete",
        method="POST",
        payload={
            "external_event_id": event_id,
            "external_event_link": event_link,
            "error_message": error,
        },
    )


def parse_dt(value: str) -> datetime:
    # Pydantic serializes aware datetimes as ISO strings. Google wants RFC3339.
    value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt


def event_body(req: dict[str, Any]) -> dict[str, Any]:
    start = parse_dt(req["starts_at"]).astimezone(TZ)
    end = parse_dt(req["ends_at"]).astimezone(TZ)
    # Older requests already contain generated relative/full links. Strip only
    # this task's exact machine footer; preserve all other user-supplied text.
    legacy = re.compile(
        r"^Personal OS task:\s+(?:/tasks|https?://[^\s]+/tasks)\?task="
        + re.escape(str(req["task_id"]))
        + r"$"
    )
    text = "\n".join(
        line
        for line in str(req.get("description") or "").splitlines()
        if not legacy.fullmatch(line.strip())
    ).strip()
    description_parts = [escape(text).replace("\n", "<br>")] if text else []
    task_url = f"{TASK_URL_BASE}?task={req['task_id']}"
    description_parts.append(
        f'<a href="{escape(task_url, quote=True)}">Otevřít úkol v Personal OS</a>'
    )
    body: dict[str, Any] = {
        "summary": req["title"],
        "description": "<br><br>".join(description_parts),
    }
    if req.get("all_day"):
        body["start"] = {"date": start.date().isoformat(), "timeZone": "Europe/Prague"}
        body["end"] = {"date": end.date().isoformat(), "timeZone": "Europe/Prague"}
    else:
        body["start"] = {"dateTime": start.isoformat(), "timeZone": "Europe/Prague"}
        body["end"] = {"dateTime": end.isoformat(), "timeZone": "Europe/Prague"}
    reminder = req.get("reminder_minutes")
    if reminder is not None:
        body["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": int(reminder)}],
        }
    return body


def create_event(service: Any, req: dict[str, Any]) -> tuple[str, str | None]:
    response = (
        service.events()
        .insert(
            calendarId=req["calendar_external_id"],
            body=event_body(req),
            sendUpdates="none",
        )
        .execute()
    )
    return response["id"], response.get("htmlLink")


def update_event(service: Any, req: dict[str, Any]) -> tuple[str, str | None]:
    event_id = req.get("external_event_id")
    if not event_id:
        return create_event(service, req)
    response = (
        service.events()
        .patch(
            calendarId=req["calendar_external_id"],
            eventId=event_id,
            body=event_body(req),
            sendUpdates="none",
        )
        .execute()
    )
    return response["id"], response.get("htmlLink")


def delete_event(service: Any, req: dict[str, Any]) -> tuple[str | None, str | None]:
    event_id = req.get("external_event_id")
    if not event_id:
        return None, None
    try:
        service.events().delete(
            calendarId=req["calendar_external_id"],
            eventId=event_id,
            sendUpdates="none",
        ).execute()
    except HttpError as exc:
        if (
            getattr(exc, "status_code", None) == 404
            or getattr(exc.resp, "status", None) == 404
        ):
            return event_id, None
        raise
    return event_id, None


def process_one(service: Any, req: dict[str, Any], stats: RunStats) -> None:
    stats.processed += 1
    request_id = req["id"]
    claimed = claim(request_id)
    if not claimed:
        return
    try:
        operation = claimed["operation"]
        if operation == "create":
            event_id, link = create_event(service, claimed)
        elif operation == "update":
            event_id, link = update_event(service, claimed)
        elif operation == "delete":
            event_id, link = delete_event(service, claimed)
        else:
            raise RuntimeError(f"Unsupported calendar operation: {operation}")
        complete(request_id, event_id=event_id, event_link=link)
        stats.completed += 1
    except Exception as exc:  # complete as failed so UI shows retry
        stats.failed += 1
        err = f"{type(exc).__name__}: {exc}"
        try:
            complete(
                request_id,
                event_id=claimed.get("external_event_id"),
                event_link=claimed.get("external_event_link"),
                error=err[:4000],
            )
        except Exception as complete_exc:
            stats.add(
                f"Nepodařilo se označit calendar request {request_id} jako failed: {complete_exc!r}"
            )
        stats.add(f"Calendar request {request_id} selhal: {err}")


def main() -> int:
    stats = RunStats()
    try:
        service = calendar_service()
        sync_calendars_if_due(service, stats)
        for req in pending_requests()[:MAX_PER_RUN]:
            process_one(service, req, stats)
    except Exception as exc:
        print(f"⚠️ Personal OS calendar writer selhal: {type(exc).__name__}: {exc}")
        return 1
    if stats.messages:
        print("\n".join(stats.messages))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
