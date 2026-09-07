import json
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, cast

from fastapi import Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, StreamingResponse

from app.db.session import AsyncSessionLocal
from app.models.agent_action import AgentAction, AgentActionType
from app.models.note import Note
from app.models.task import Task, TaskStatus
from app.schemas.note import NoteRead
from app.schemas.task import TaskRead
from app.services.api_key_service import verify_api_key

RouteHandler = Callable[[Request], Awaitable[Response]]
JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
SessionMaker = Callable[[], AbstractAsyncContextManager[AsyncSession]]

_TASK_RE = re.compile(r"^/tasks(?:/(?P<id>[0-9a-fA-F-]{36}))?$")
_NOTE_RE = re.compile(r"^/notes(?:/(?P<id>[0-9a-fA-F-]{36}))?$")


def jsonable_model(model: object, schema: type[TaskRead] | type[NoteRead]) -> dict[str, Any]:
    return schema.model_validate(model).model_dump(mode="json")


def _safe_json(data: bytes) -> JsonValue:
    if not data:
        return None
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return data.decode("utf-8", errors="replace")
    if isinstance(parsed, dict | list | str | int | float | bool) or parsed is None:
        return parsed
    return str(parsed)


def _route_info(
    method: str, path: str, payload: JsonValue
) -> tuple[str, str, uuid.UUID | None] | None:
    if method not in {"POST", "PATCH", "DELETE"}:
        return None
    task_match = _TASK_RE.match(path)
    if task_match:
        raw_id = task_match.group("id")
        if method == "POST" and raw_id is None:
            return (AgentActionType.CREATE_TASK.value, "task", None)
        if method == "PATCH" and raw_id:
            if isinstance(payload, dict) and payload.get("status") == TaskStatus.DONE.value:
                return (AgentActionType.COMPLETE_TASK.value, "task", uuid.UUID(raw_id))
            return (AgentActionType.UPDATE_TASK.value, "task", uuid.UUID(raw_id))
        if method == "DELETE" and raw_id:
            return ("delete_task", "task", uuid.UUID(raw_id))
    note_match = _NOTE_RE.match(path)
    if note_match:
        raw_id = note_match.group("id")
        if method == "POST" and raw_id is None:
            return (AgentActionType.ADD_NOTE.value, "note", None)
        if method == "PATCH" and raw_id:
            return (AgentActionType.UPDATE_NOTE.value, "note", uuid.UUID(raw_id))
        if method == "DELETE" and raw_id:
            return ("delete_note", "note", uuid.UUID(raw_id))
    return None


def _sessionmaker(request: Request) -> SessionMaker:
    maybe_sessionmaker = getattr(request.app.state, "agent_action_sessionmaker", AsyncSessionLocal)
    return cast(SessionMaker, maybe_sessionmaker)


async def _before_state(
    sessionmaker: SessionMaker, entity_type: str, entity_id: uuid.UUID | None, owner_id: uuid.UUID
) -> dict[str, Any] | None:
    if entity_id is None:
        return None
    async with sessionmaker() as db:
        if entity_type == "task":
            task = await db.get(Task, entity_id)
            if task is None or task.owner_id != owner_id:
                return None
            return jsonable_model(task, TaskRead)
        if entity_type == "note":
            note = await db.get(Note, entity_id)
            if note is None or note.owner_id != owner_id:
                return None
            return jsonable_model(note, NoteRead)
    return None


def _entity_id_from_result(fallback: uuid.UUID | None, result: JsonValue) -> uuid.UUID | None:
    if fallback is not None:
        return fallback
    if isinstance(result, dict) and isinstance(result.get("id"), str):
        try:
            return uuid.UUID(result["id"])
        except ValueError:
            return None
    return None


async def _log_action(
    *,
    sessionmaker: SessionMaker,
    owner_id: uuid.UUID,
    api_key_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    payload: JsonValue,
    before: dict[str, Any] | None,
    result: JsonValue,
    reasoning: str,
    source: str,
    source_system: str | None,
    batch_id: str | None,
    latency_ms: int,
) -> None:
    async with sessionmaker() as db:
        db.add(
            AgentAction(
                owner_id=owner_id,
                api_key_id=api_key_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                payload_json=payload,
                before_json=before,
                result_json=result,
                reasoning=reasoning,
                source=source,
                source_system=source_system,
                batch_id=batch_id,
                latency_ms=latency_ms,
            )
        )
        await db.commit()


class AgentActionAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RouteHandler) -> Response:
        plaintext_key = request.headers.get("X-API-Key")
        route_info = _route_info(request.method, request.url.path, None)
        if plaintext_key is None or route_info is None:
            return await call_next(request)

        body = await request.body()
        payload = _safe_json(body)
        route_info = _route_info(request.method, request.url.path, payload)
        if route_info is None:
            return await call_next(request)

        reasoning = request.headers.get("X-Agent-Reasoning", "").strip()
        if not reasoning:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": {
                        "code": "agent_reasoning_required",
                        "message": "X-Agent-Reasoning is required for API-key mutations",
                        "field": "X-Agent-Reasoning",
                    }
                },
            )

        sessionmaker = _sessionmaker(request)
        async with sessionmaker() as db:
            identity = await verify_api_key(db, plaintext_key)
        if identity is None:
            return await call_next(request)

        action, entity_type, path_entity_id = route_info
        before = await _before_state(sessionmaker, entity_type, path_entity_id, identity.owner_id)

        started = time.perf_counter()
        response = await call_next(request)
        response_body = b""
        response_stream = cast(Any, response)
        async for chunk in response_stream.body_iterator:
            response_body += chunk
        latency_ms = int((time.perf_counter() - started) * 1000)
        result = _safe_json(response_body)

        if 200 <= response.status_code < 300:
            entity_id = _entity_id_from_result(path_entity_id, result)
            await _log_action(
                sessionmaker=sessionmaker,
                owner_id=identity.owner_id,
                api_key_id=identity.api_key_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
                before=before,
                result=result,
                reasoning=reasoning,
                source=request.headers.get("X-Agent-Source", "manual"),
                source_system=request.headers.get("X-Agent-Source-System"),
                batch_id=request.headers.get("X-Agent-Batch-Id"),
                latency_ms=latency_ms,
            )

        return StreamingResponse(
            iter([response_body]),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
