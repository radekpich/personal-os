import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_api_key_scope, verify_csrf
from app.db.session import get_db
from app.models.agent_registry import (
    AgentChannel,
    AgentConfigChange,
    AgentInstance,
    AgentIntegration,
    AgentJob,
    AgentRun,
    AgentWatch,
)
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.agent_registry import (
    AgentChannelRead,
    AgentConfigChangeRead,
    AgentInstanceRead,
    AgentIntegrationRead,
    AgentJobRead,
    AgentKeyRead,
    AgentList,
    AgentOverview,
    AgentRegistrySyncRequest,
    AgentRegistrySyncResponse,
    AgentRunRead,
    AgentRunsCreated,
    AgentRunsIn,
    AgentWatchRead,
    WatchReportIn,
)
from app.services.agent_registry_service import (
    computed_agent_status,
    get_latest_agent,
    heartbeat_agent,
    overview_counts,
    sync_registry,
)
from app.services.api_key_service import ApiKeyIdentity

router = APIRouter(prefix="/agent", tags=["agent-registry"])

agent_report_dependency = Depends(require_api_key_scope("agent:report"))


@router.post("/registry/sync", response_model=AgentRegistrySyncResponse)
async def registry_sync(
    payload: AgentRegistrySyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, agent_report_dependency],
) -> AgentRegistrySyncResponse:
    agent, idempotent, changes_created = await sync_registry(
        db, owner_id=identity.owner_id, payload=payload
    )
    return AgentRegistrySyncResponse(
        agent_id=agent.id,
        snapshot_hash=payload.snapshot_hash,
        idempotent=idempotent,
        changes_created=changes_created,
    )


@router.post("/heartbeat")
async def heartbeat(
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, agent_report_dependency],
    name: str = "hermes",
    host: str = "unknown",
    status_value: str = "running",
    last_error: str | None = None,
) -> dict[str, str]:
    agent = await heartbeat_agent(
        db,
        owner_id=identity.owner_id,
        name=name,
        host=host,
        status=status_value,
        last_error=last_error,
    )
    return {"agent_id": str(agent.id), "status": agent.status}


@router.get("/overview", response_model=AgentOverview)
async def overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentOverview:
    agent = await get_latest_agent(db, current_user.id)
    counts = await overview_counts(db, agent)
    if agent is None:
        agent_read = None
    else:
        agent_read = AgentInstanceRead.model_validate(agent).model_copy(
            update={"status": computed_agent_status(agent)}
        )
    return AgentOverview(agent=agent_read, **counts)


async def _latest_owned_agent(db: AsyncSession, user: User) -> AgentInstance:
    agent = await get_latest_agent(db, user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")
    return agent


def _list_response(items: list[BaseModel], total: int, *, page: int, page_size: int) -> AgentList:
    return AgentList(
        items=[item.model_dump(mode="json") for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/runs", response_model=AgentRunsCreated)
async def create_runs(
    payload: AgentRunsIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, agent_report_dependency],
) -> AgentRunsCreated:
    agent = await get_latest_agent(db, identity.owner_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")
    created = 0
    for item in payload.runs:
        job_id = item.job_id
        if job_id is not None:
            job = await db.get(AgentJob, job_id)
            if job is None or job.agent_id != agent.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
            job.last_run_at = item.started_at
            job.last_status = item.status
            job.last_duration_ms = item.duration_ms
            job.run_count += 1
            job.consecutive_failures = (
                0 if item.status == "success" else job.consecutive_failures + 1
            )
            db.add(job)
        db.add(AgentRun(agent_id=agent.id, **item.model_dump()))
        created += 1
    await db.commit()
    return AgentRunsCreated(created=created)


@router.post("/watches/{watch_id}/report")
async def report_watch(
    watch_id: uuid.UUID,
    payload: WatchReportIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[ApiKeyIdentity, agent_report_dependency],
) -> dict[str, str]:
    agent = await get_latest_agent(db, identity.owner_id)
    watch = await db.get(AgentWatch, watch_id)
    if agent is None or watch is None or watch.agent_id != agent.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="watch not found")
    watch.last_checked_at = payload.checked_at
    watch.last_result = payload.result
    if payload.triggered:
        watch.last_triggered_at = payload.checked_at
        watch.trigger_count += 1
    db.add(watch)
    await db.commit()
    return {"status": "recorded"}


@router.get("/channels", response_model=AgentList)
async def list_channels(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 100,
) -> AgentList:
    agent = await _latest_owned_agent(db, current_user)
    total = await db.scalar(
        select(func.count()).select_from(AgentChannel).where(AgentChannel.agent_id == agent.id)
    )
    rows = (
        (
            await db.execute(
                select(AgentChannel)
                .where(AgentChannel.agent_id == agent.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return _list_response(
        [AgentChannelRead.model_validate(row) for row in rows],
        total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/runs", response_model=AgentList)
async def list_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    job_id: uuid.UUID | None = None,
    trigger: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    q: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AgentList:
    agent = await _latest_owned_agent(db, current_user)
    conditions = [AgentRun.agent_id == agent.id]
    if job_id is not None:
        conditions.append(AgentRun.job_id == job_id)
    if trigger:
        conditions.append(AgentRun.trigger == trigger)
    if status_filter:
        conditions.append(AgentRun.status == status_filter)
    if q:
        conditions.append(AgentRun.summary.ilike(f"%{q}%"))
    total = (
        await db.execute(select(func.count()).select_from(AgentRun).where(*conditions))
    ).scalar_one()
    rows = (
        (
            await db.execute(
                select(AgentRun)
                .where(*conditions)
                .order_by(AgentRun.started_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return _list_response(
        [AgentRunRead.model_validate(row) for row in rows], total, page=page, page_size=page_size
    )


@router.get("/jobs", response_model=AgentList)
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentList:
    agent = await _latest_owned_agent(db, current_user)
    rows = (
        (
            await db.execute(
                select(AgentJob)
                .where(AgentJob.agent_id == agent.id)
                .order_by(AgentJob.next_run_at.asc().nullslast())
            )
        )
        .scalars()
        .all()
    )
    return _list_response(
        [AgentJobRead.model_validate(row) for row in rows], len(rows), page=1, page_size=50
    )


@router.get("/integrations", response_model=AgentList)
async def list_integrations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentList:
    agent = await _latest_owned_agent(db, current_user)
    rows = (
        (
            await db.execute(
                select(AgentIntegration)
                .where(AgentIntegration.agent_id == agent.id)
                .order_by(AgentIntegration.kind, AgentIntegration.name)
            )
        )
        .scalars()
        .all()
    )
    return _list_response(
        [AgentIntegrationRead.model_validate(row) for row in rows], len(rows), page=1, page_size=50
    )


@router.get("/watches", response_model=AgentList)
async def list_watches(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentList:
    agent = await _latest_owned_agent(db, current_user)
    rows = (
        (
            await db.execute(
                select(AgentWatch).where(AgentWatch.agent_id == agent.id).order_by(AgentWatch.name)
            )
        )
        .scalars()
        .all()
    )
    return _list_response(
        [AgentWatchRead.model_validate(row) for row in rows], len(rows), page=1, page_size=50
    )


@router.get("/config-changes", response_model=AgentList)
async def list_config_changes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    acknowledged: bool | None = None,
) -> AgentList:
    agent = await _latest_owned_agent(db, current_user)
    conditions = [AgentConfigChange.agent_id == agent.id]
    if acknowledged is True:
        conditions.append(AgentConfigChange.acknowledged_at.is_not(None))
    elif acknowledged is False:
        conditions.append(AgentConfigChange.acknowledged_at.is_(None))
    rows = (
        (
            await db.execute(
                select(AgentConfigChange)
                .where(*conditions)
                .order_by(AgentConfigChange.timestamp.desc())
            )
        )
        .scalars()
        .all()
    )
    return _list_response(
        [AgentConfigChangeRead.model_validate(row) for row in rows], len(rows), page=1, page_size=50
    )


@router.get("/keys", response_model=AgentList)
async def list_agent_keys(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentList:
    rows = (
        (
            await db.execute(
                select(ApiKey)
                .where(ApiKey.owner_id == current_user.id, ApiKey.scopes.is_not(None))
                .order_by(ApiKey.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return _list_response(
        [AgentKeyRead.model_validate(row) for row in rows], len(rows), page=1, page_size=50
    )


@router.post("/keys/revoke-all", dependencies=[Depends(verify_csrf)])
async def revoke_all_agent_keys(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, int]:
    now = datetime.now(UTC)
    rows = (
        (
            await db.execute(
                select(ApiKey).where(
                    ApiKey.owner_id == current_user.id, ApiKey.revoked_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.revoked_at = now
        db.add(row)
    await db.commit()
    return {"revoked_count": len(rows)}


@router.post("/config-changes/{change_id}/acknowledge", dependencies=[Depends(verify_csrf)])
async def acknowledge_config_change(
    change_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    change = (
        await db.execute(
            select(AgentConfigChange)
            .join(AgentInstance, AgentInstance.id == AgentConfigChange.agent_id)
            .where(AgentConfigChange.id == change_id, AgentInstance.owner_id == current_user.id)
        )
    ).scalar_one_or_none()
    if change is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="change not found")
    change.acknowledged_at = datetime.now(UTC)
    db.add(change)
    await db.commit()
    return {"status": "acknowledged"}
