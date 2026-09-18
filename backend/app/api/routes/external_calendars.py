import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ActorContext,
    get_current_actor,
    require_api_key_scope,
    verify_csrf_or_api_key,
)
from app.db.session import get_db
from app.models.external_calendar import CalendarRequestStatus
from app.schemas.external_calendar import (
    CalendarRequestComplete,
    CalendarRequestCreate,
    CalendarRequestList,
    CalendarRequestRead,
    ExternalCalendarList,
    ExternalCalendarSyncRequest,
    ExternalCalendarUpdate,
)
from app.services import external_calendar_service
from app.services.api_key_service import ApiKeyIdentity

router = APIRouter(tags=["external-calendars"])


@router.get("/external-calendars", response_model=ExternalCalendarList)
async def list_external_calendars(
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> ExternalCalendarList:
    return ExternalCalendarList(
        items=await external_calendar_service.list_calendars(db, actor_context.user)
    )


@router.patch(
    "/external-calendars/{calendar_id}",
    response_model=ExternalCalendarList,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def update_external_calendar(
    calendar_id: uuid.UUID,
    payload: ExternalCalendarUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> ExternalCalendarList:
    await external_calendar_service.update_calendar(db, actor_context.user, calendar_id, payload)
    return ExternalCalendarList(
        items=await external_calendar_service.list_calendars(db, actor_context.user)
    )


@router.post(
    "/agent/calendars/sync",
    response_model=ExternalCalendarList,
    dependencies=[Depends(require_api_key_scope("calendar:report"))],
)
async def sync_agent_calendars(
    payload: ExternalCalendarSyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, Depends(require_api_key_scope("calendar:report"))],
) -> ExternalCalendarList:
    calendars = await external_calendar_service.sync_calendars(db, identity.owner_id, payload)
    return ExternalCalendarList(items=calendars)


@router.post(
    "/tasks/{task_id}/calendar-request",
    response_model=CalendarRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def create_task_calendar_request(
    task_id: uuid.UUID,
    payload: CalendarRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> CalendarRequestRead:
    request = await external_calendar_service.create_request(
        db, actor_context.user, task_id, payload
    )
    return await external_calendar_service.serialize_request(db, request)


@router.delete(
    "/calendar-requests/{request_id}",
    response_model=CalendarRequestRead,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def cancel_calendar_request(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> CalendarRequestRead:
    request = await external_calendar_service.cancel_request(db, actor_context.user, request_id)
    return await external_calendar_service.serialize_request(db, request)


@router.post(
    "/calendar-requests/{request_id}/retry",
    response_model=CalendarRequestRead,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def retry_calendar_request(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> CalendarRequestRead:
    request = await external_calendar_service.retry_request(db, actor_context.user, request_id)
    return await external_calendar_service.serialize_request(db, request)


@router.post(
    "/calendar-requests/{request_id}/disconnect",
    response_model=CalendarRequestRead,
    dependencies=[Depends(verify_csrf_or_api_key)],
)
async def disconnect_calendar_request(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor_context: Annotated[ActorContext, Depends(get_current_actor)],
) -> CalendarRequestRead:
    request = await external_calendar_service.disconnect_request(db, actor_context.user, request_id)
    return await external_calendar_service.serialize_request(db, request)


@router.get(
    "/agent/calendar-requests",
    response_model=CalendarRequestList,
    dependencies=[Depends(require_api_key_scope("calendar:write"))],
)
async def agent_calendar_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, Depends(require_api_key_scope("calendar:write"))],
    status_filter: Annotated[
        CalendarRequestStatus, Query(alias="status")
    ] = CalendarRequestStatus.PENDING,
) -> CalendarRequestList:
    requests = await external_calendar_service.pending_requests(
        db, identity.owner_id, status_filter
    )
    return CalendarRequestList(
        items=[
            await external_calendar_service.serialize_request(db, request) for request in requests
        ]
    )


@router.post(
    "/agent/calendar-requests/{request_id}/claim",
    response_model=CalendarRequestRead,
    dependencies=[Depends(require_api_key_scope("calendar:write"))],
)
async def claim_calendar_request(
    request_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, Depends(require_api_key_scope("calendar:write"))],
) -> CalendarRequestRead:
    request = await external_calendar_service.claim_request(
        db, identity.owner_id, request_id, identity.api_key_id
    )
    return await external_calendar_service.serialize_request(db, request)


@router.post(
    "/agent/calendar-requests/{request_id}/complete",
    response_model=CalendarRequestRead,
    dependencies=[Depends(require_api_key_scope("calendar:write"))],
)
async def complete_calendar_request(
    request_id: uuid.UUID,
    payload: CalendarRequestComplete,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, Depends(require_api_key_scope("calendar:write"))],
) -> CalendarRequestRead:
    request = await external_calendar_service.complete_request(
        db, identity.owner_id, request_id, payload
    )
    return await external_calendar_service.serialize_request(db, request)
