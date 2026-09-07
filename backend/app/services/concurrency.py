import enum
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel


class MutationActor(str, enum.Enum):
    USER = "user"
    AGENT = "agent"


class ConflictError(Exception):
    def __init__(self, code: str, message: str, current_state: dict[str, Any]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.current_state = current_state


class VersionConflict(ConflictError):
    def __init__(self, current_state: dict[str, Any]) -> None:
        super().__init__(
            "version_conflict",
            "Record version does not match If-Match",
            current_state,
        )


class FreshUserEditConflict(ConflictError):
    def __init__(self, current_state: dict[str, Any]) -> None:
        super().__init__(
            "fresh_user_edit",
            "Record was recently edited by user; agent update is blocked",
            current_state,
        )


def state_from_schema(schema: type[BaseModel], entity: object) -> dict[str, Any]:
    return schema.model_validate(entity).model_dump(mode="json")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def ensure_can_mutate(
    entity: Any,
    *,
    expected_version: int | None,
    actor: MutationActor,
    current_state: dict[str, Any],
    fresh_user_edit_guard_minutes: int,
) -> None:
    if expected_version is None:
        raise ValueError("expected_version is required")
    if entity.version != expected_version:
        raise VersionConflict(current_state)
    if (
        actor == MutationActor.AGENT
        and entity.updated_by == MutationActor.USER.value
        and datetime.now(UTC) - _aware(entity.updated_at)
        < timedelta(minutes=fresh_user_edit_guard_minutes)
    ):
        raise FreshUserEditConflict(current_state)


def apply_mutation_audit(
    entity: Any,
    *,
    actor: MutationActor,
    api_key_id: uuid.UUID | None = None,
) -> None:
    entity.version += 1
    entity.updated_by = actor.value
    entity.api_key_id = api_key_id
