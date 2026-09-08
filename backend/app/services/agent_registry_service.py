import uuid
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any, TypeVar, cast

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_registry import (
    AgentCapability,
    AgentChannel,
    AgentConfigChange,
    AgentInstance,
    AgentIntegration,
    AgentJob,
    AgentRun,
    AgentRunDailySummary,
    AgentWatch,
)
from app.schemas.agent_registry import (
    AgentCapabilityIn,
    AgentChannelIn,
    AgentIntegrationIn,
    AgentJobIn,
    AgentRegistrySyncRequest,
    AgentWatchIn,
)

RegistryChild = AgentJob | AgentIntegration | AgentWatch | AgentChannel | AgentCapability
Payload = AgentJobIn | AgentIntegrationIn | AgentWatchIn | AgentChannelIn | AgentCapabilityIn
NamedRegistryChild = AgentJob | AgentIntegration | AgentWatch | AgentCapability
NamedPayload = AgentJobIn | AgentIntegrationIn | AgentWatchIn | AgentCapabilityIn
ModelT = TypeVar("ModelT", AgentJob, AgentIntegration, AgentWatch, AgentCapability)
PayloadT = TypeVar("PayloadT", AgentJobIn, AgentIntegrationIn, AgentWatchIn, AgentCapabilityIn)

STALE_AFTER_MINUTES = 15
JOB_GRACE_MINUTES = 5
JOB_CONFIG_FIELDS = {
    "name",
    "description",
    "schedule",
    "schedule_description",
    "is_enabled",
    "tags",
}
INTEGRATION_CONFIG_FIELDS = {"name", "kind", "scopes", "notes"}
WATCH_CONFIG_FIELDS = {"name", "description", "kind", "config_json", "schedule", "is_active"}
CHANNEL_CONFIG_FIELDS = {"channel_type", "identifier", "is_active"}
CAPABILITY_CONFIG_FIELDS = {"name", "description", "is_enabled", "metadata_json"}


def now_utc() -> datetime:
    return datetime.now(UTC)


def _public_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _public_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_public_value(item) for item in value]
    return value


def _payload_dump(payload: Payload) -> dict[str, Any]:
    return cast(dict[str, Any], _public_value(payload.model_dump(exclude_unset=False)))


def _config_fields_for(target_type: str) -> set[str]:
    return {
        "job": JOB_CONFIG_FIELDS,
        "integration": INTEGRATION_CONFIG_FIELDS,
        "watch": WATCH_CONFIG_FIELDS,
        "channel": CHANNEL_CONFIG_FIELDS,
        "capability": CAPABILITY_CONFIG_FIELDS,
    }[target_type]


def _record_dump(record: RegistryChild, *, target_type: str | None = None) -> dict[str, Any]:
    ignored = {"id", "agent_id", "created_at", "updated_at", "last_snapshot_hash"}
    allowed = _config_fields_for(target_type) if target_type else None
    data: dict[str, Any] = {}
    for column in record.__table__.columns:
        if column.name in ignored or (allowed is not None and column.name not in allowed):
            continue
        data[column.name] = _public_value(getattr(record, column.name))
    return data


def _list_names(items: Iterable[NamedPayload]) -> set[str]:
    return {item.name for item in items}


def _make_change(
    agent_id: uuid.UUID,
    change_type: str,
    target_type: str,
    target_name: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> AgentConfigChange:
    return AgentConfigChange(
        agent_id=agent_id,
        change_type=change_type,
        target_type=target_type,
        target_name=target_name,
        diff_json={"before": before, "after": after},
    )


async def get_or_create_agent(
    db: AsyncSession, owner_id: uuid.UUID, payload: AgentRegistrySyncRequest
) -> AgentInstance:
    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.owner_id == owner_id,
            AgentInstance.name == payload.agent.name,
            AgentInstance.host == payload.agent.host,
        )
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        agent = AgentInstance(
            owner_id=owner_id,
            name=payload.agent.name,
            host=payload.agent.host,
            version=payload.agent.version,
            started_at=payload.agent.started_at,
            last_heartbeat_at=now_utc(),
            status="running",
            config_hash=None,
        )
        db.add(agent)
        await db.flush()
        return agent
    agent.version = payload.agent.version
    agent.started_at = payload.agent.started_at
    agent.last_heartbeat_at = now_utc()
    agent.status = "running"
    return agent


async def _sync_named_children(
    db: AsyncSession,
    *,
    agent: AgentInstance,
    model: type[ModelT],
    payloads: list[PayloadT],
    target_type: str,
    snapshot_hash: str,
) -> list[AgentConfigChange]:
    existing = (await db.execute(select(model).where(model.agent_id == agent.id))).scalars().all()
    existing_by_name = {item.name: item for item in existing}
    seen_names = _list_names(payloads)
    changes: list[AgentConfigChange] = []

    for payload in payloads:
        config_fields = _config_fields_for(target_type)
        after = {
            key: value for key, value in _payload_dump(payload).items() if key in config_fields
        }
        record = existing_by_name.get(payload.name)
        if record is None:
            record = model(agent_id=agent.id, **payload.model_dump(exclude={"added_at"}))
            if (
                isinstance(record, AgentIntegration)
                and isinstance(payload, AgentIntegrationIn)
                and payload.added_at is not None
            ):
                record.added_at = payload.added_at
            record.last_snapshot_hash = snapshot_hash
            db.add(record)
            await db.flush()
            changes.append(_make_change(agent.id, "added", target_type, payload.name, None, after))
            continue

        before = _record_dump(record, target_type=target_type)
        config_changed = False
        values = payload.model_dump(exclude={"added_at"})
        for key, value in values.items():
            if getattr(record, key) != value:
                setattr(record, key, value)
                if key in config_fields:
                    config_changed = True
        if (
            isinstance(record, AgentIntegration)
            and isinstance(payload, AgentIntegrationIn)
            and payload.added_at is not None
            and record.added_at != payload.added_at
        ):
            record.added_at = payload.added_at
        if config_changed:
            changes.append(
                _make_change(agent.id, "updated", target_type, payload.name, before, after)
            )
        record.last_snapshot_hash = snapshot_hash
        db.add(record)

    removed = [item for item in existing if item.name not in seen_names]
    for record in removed:
        before = _record_dump(record, target_type=target_type)
        changes.append(_make_change(agent.id, "removed", target_type, record.name, before, None))
        await db.delete(record)

    return changes


async def _sync_channels(
    db: AsyncSession, *, agent: AgentInstance, payloads: list[AgentChannelIn], snapshot_hash: str
) -> list[AgentConfigChange]:
    existing = (
        (await db.execute(select(AgentChannel).where(AgentChannel.agent_id == agent.id)))
        .scalars()
        .all()
    )
    existing_by_key = {(item.channel_type, item.identifier): item for item in existing}
    seen = {(item.channel_type, item.identifier) for item in payloads}
    changes: list[AgentConfigChange] = []
    for payload in payloads:
        key = (payload.channel_type, payload.identifier)
        target_name = f"{payload.channel_type}:{payload.identifier}"
        after = {
            key: value
            for key, value in _payload_dump(payload).items()
            if key in CHANNEL_CONFIG_FIELDS
        }
        record = existing_by_key.get(key)
        if record is None:
            record = AgentChannel(agent_id=agent.id, **payload.model_dump())
            record.last_snapshot_hash = snapshot_hash
            db.add(record)
            changes.append(_make_change(agent.id, "added", "channel", target_name, None, after))
            continue
        before = _record_dump(record, target_type="channel")
        config_changed = False
        for field, value in payload.model_dump().items():
            if getattr(record, field) != value:
                setattr(record, field, value)
                if field in CHANNEL_CONFIG_FIELDS:
                    config_changed = True
        if config_changed:
            changes.append(_make_change(agent.id, "updated", "channel", target_name, before, after))
        record.last_snapshot_hash = snapshot_hash
        db.add(record)

    for record in existing:
        if (record.channel_type, record.identifier) not in seen:
            before = _record_dump(record, target_type="channel")
            changes.append(
                _make_change(
                    agent.id,
                    "removed",
                    "channel",
                    f"{record.channel_type}:{record.identifier}",
                    before,
                    None,
                )
            )
            await db.delete(record)
    return changes


async def sync_registry(
    db: AsyncSession, *, owner_id: uuid.UUID, payload: AgentRegistrySyncRequest
) -> tuple[AgentInstance, bool, int]:
    agent = await get_or_create_agent(db, owner_id, payload)
    if agent.config_hash == payload.snapshot_hash:
        agent.last_heartbeat_at = now_utc()
        agent.status = "running"
        await db.commit()
        await db.refresh(agent)
        return agent, True, 0

    changes: list[AgentConfigChange] = []
    changes.extend(
        await _sync_named_children(
            db,
            agent=agent,
            model=AgentJob,
            payloads=payload.jobs,
            target_type="job",
            snapshot_hash=payload.snapshot_hash,
        )
    )
    changes.extend(
        await _sync_named_children(
            db,
            agent=agent,
            model=AgentIntegration,
            payloads=payload.integrations,
            target_type="integration",
            snapshot_hash=payload.snapshot_hash,
        )
    )
    changes.extend(
        await _sync_named_children(
            db,
            agent=agent,
            model=AgentWatch,
            payloads=payload.watches,
            target_type="watch",
            snapshot_hash=payload.snapshot_hash,
        )
    )
    changes.extend(
        await _sync_named_children(
            db,
            agent=agent,
            model=AgentCapability,
            payloads=payload.capabilities,
            target_type="capability",
            snapshot_hash=payload.snapshot_hash,
        )
    )
    changes.extend(
        await _sync_channels(
            db, agent=agent, payloads=payload.channels, snapshot_hash=payload.snapshot_hash
        )
    )
    for change in changes:
        db.add(change)
    agent.config_hash = payload.snapshot_hash
    agent.last_heartbeat_at = now_utc()
    agent.status = "running"
    await db.commit()
    await db.refresh(agent)
    return agent, False, len(changes)


async def heartbeat_agent(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    name: str,
    host: str,
    status: str = "running",
    last_error: str | None = None,
) -> AgentInstance:
    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.owner_id == owner_id,
            AgentInstance.name == name,
            AgentInstance.host == host,
        )
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        agent = AgentInstance(
            owner_id=owner_id, name=name, host=host, status=status, last_error=last_error
        )
        db.add(agent)
    agent.last_heartbeat_at = now_utc()
    agent.status = status
    agent.last_error = last_error
    await db.commit()
    await db.refresh(agent)
    return agent


def computed_agent_status(agent: AgentInstance | None, *, at: datetime | None = None) -> str:
    if agent is None or agent.last_heartbeat_at is None:
        return "unknown"
    current = at or now_utc()
    heartbeat = agent.last_heartbeat_at
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=UTC)
    if heartbeat < current - timedelta(minutes=STALE_AFTER_MINUTES):
        return "stale"
    return agent.status or "running"


async def get_latest_agent(db: AsyncSession, owner_id: uuid.UUID) -> AgentInstance | None:
    return (
        await db.execute(
            select(AgentInstance)
            .where(AgentInstance.owner_id == owner_id)
            .order_by(
                AgentInstance.last_heartbeat_at.desc().nullslast(), AgentInstance.created_at.desc()
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def overview_counts(db: AsyncSession, agent: AgentInstance | None) -> dict[str, Any]:
    if agent is None:
        return {
            "active_job_count": 0,
            "active_integration_count": 0,
            "run_count_24h": 0,
            "cost_estimate_month": 0.0,
            "unacknowledged_change_count": 0,
            "warnings": ["Agent zatím neposlal registry snapshot."],
        }
    since_24h = now_utc() - timedelta(hours=24)
    since_month = now_utc() - timedelta(days=30)
    active_job_count = (
        await db.execute(
            select(func.count())
            .select_from(AgentJob)
            .where(AgentJob.agent_id == agent.id, AgentJob.is_enabled.is_(True))
        )
    ).scalar_one()
    active_integration_count = (
        await db.execute(
            select(func.count())
            .select_from(AgentIntegration)
            .where(AgentIntegration.agent_id == agent.id, AgentIntegration.status == "active")
        )
    ).scalar_one()
    run_count_24h = (
        await db.execute(
            select(func.count())
            .select_from(AgentRun)
            .where(AgentRun.agent_id == agent.id, AgentRun.started_at >= since_24h)
        )
    ).scalar_one()
    cost_estimate_month = (
        await db.execute(
            select(func.coalesce(func.sum(AgentRun.cost_estimate), 0.0)).where(
                AgentRun.agent_id == agent.id, AgentRun.started_at >= since_month
            )
        )
    ).scalar_one()
    unacknowledged_change_count = (
        await db.execute(
            select(func.count())
            .select_from(AgentConfigChange)
            .where(
                AgentConfigChange.agent_id == agent.id, AgentConfigChange.acknowledged_at.is_(None)
            )
        )
    ).scalar_one()
    warnings: list[str] = []
    if computed_agent_status(agent) == "stale":
        warnings.append("Heartbeat agenta je zastaralý.")
    overdue_jobs = (
        (
            await db.execute(
                select(AgentJob.name).where(
                    AgentJob.agent_id == agent.id,
                    AgentJob.is_enabled.is_(True),
                    AgentJob.next_run_at.is_not(None),
                    AgentJob.next_run_at < now_utc() - timedelta(minutes=JOB_GRACE_MINUTES),
                )
            )
        )
        .scalars()
        .all()
    )
    for name in overdue_jobs:
        warnings.append(f"Úloha {name} se nespustila v očekávaném čase.")
    failing_jobs = (
        (
            await db.execute(
                select(AgentJob.name).where(
                    AgentJob.agent_id == agent.id, AgentJob.consecutive_failures >= 3
                )
            )
        )
        .scalars()
        .all()
    )
    for name in failing_jobs:
        warnings.append(f"Úloha {name} opakovaně selhává.")
    broken_integrations = (
        (
            await db.execute(
                select(AgentIntegration.name).where(
                    AgentIntegration.agent_id == agent.id,
                    AgentIntegration.status.in_(["error", "expired"]),
                )
            )
        )
        .scalars()
        .all()
    )
    for name in broken_integrations:
        warnings.append(f"Integrace {name} je ve stavu error/expired.")
    if unacknowledged_change_count:
        warnings.append("Existují nepotvrzené změny konfigurace agenta.")
    return {
        "active_job_count": active_job_count,
        "active_integration_count": active_integration_count,
        "run_count_24h": run_count_24h,
        "cost_estimate_month": float(cost_estimate_month or 0.0),
        "unacknowledged_change_count": unacknowledged_change_count,
        "warnings": warnings,
    }


async def aggregate_old_agent_runs(db: AsyncSession, *, retention_days: int = 90) -> dict[str, int]:
    cutoff = now_utc() - timedelta(days=retention_days)
    old_runs = (
        (
            await db.execute(
                select(AgentRun)
                .where(AgentRun.started_at < cutoff)
                .order_by(AgentRun.started_at.asc())
            )
        )
        .scalars()
        .all()
    )
    grouped: dict[tuple[uuid.UUID, date], list[AgentRun]] = {}
    for run in old_runs:
        grouped.setdefault((run.agent_id, run.started_at.date()), []).append(run)

    summaries_upserted = 0
    for (agent_id, day), runs in grouped.items():
        existing = (
            await db.execute(
                select(AgentRunDailySummary).where(
                    AgentRunDailySummary.agent_id == agent_id,
                    AgentRunDailySummary.day == day,
                )
            )
        ).scalar_one_or_none()
        success_count = sum(1 for run in runs if run.status == "success")
        failure_count = len(runs) - success_count
        total_duration_ms = sum(run.duration_ms or 0 for run in runs)
        total_tokens_used = sum(run.tokens_used or 0 for run in runs)
        total_cost_estimate = sum(run.cost_estimate or 0.0 for run in runs)
        summaries = [run.summary for run in runs[:20]]
        if existing is None:
            existing = AgentRunDailySummary(
                agent_id=agent_id,
                day=day,
                run_count=0,
                success_count=0,
                failure_count=0,
                total_duration_ms=0,
                total_tokens_used=0,
                total_cost_estimate=0.0,
                summaries=[],
            )
        existing.run_count += len(runs)
        existing.success_count += success_count
        existing.failure_count += failure_count
        existing.total_duration_ms += total_duration_ms
        existing.total_tokens_used += total_tokens_used
        existing.total_cost_estimate += total_cost_estimate
        existing.summaries = [*existing.summaries, *summaries][:50]
        db.add(existing)
        summaries_upserted += 1

    for run in old_runs:
        await db.delete(run)
    await db.commit()
    return {"summaries_upserted": summaries_upserted, "runs_deleted": len(old_runs)}


async def delete_runs_older_than(db: AsyncSession, cutoff: datetime) -> int:
    result = await db.execute(delete(AgentRun).where(AgentRun.started_at < cutoff))
    await db.commit()
    return int(result.rowcount or 0)
