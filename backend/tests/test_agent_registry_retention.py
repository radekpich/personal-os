import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.agent_registry import AgentInstance, AgentRun, AgentRunDailySummary
from app.services.agent_registry_service import aggregate_old_agent_runs
from tests.conftest import TestSessionLocal


async def test_aggregate_old_agent_runs_rolls_up_and_deletes_details(setup_db: None) -> None:
    old_day = datetime.now(UTC) - timedelta(days=120)
    recent = datetime.now(UTC) - timedelta(days=3)
    async with TestSessionLocal() as session:
        agent = AgentInstance(owner_id=uuid.uuid4(), name="hermes", host="host", status="running")
        session.add(agent)
        await session.flush()
        session.add_all(
            [
                AgentRun(
                    agent_id=agent.id,
                    trigger="schedule",
                    summary="Old ok",
                    status="success",
                    started_at=old_day,
                    duration_ms=100,
                    tokens_used=10,
                    cost_estimate=0.01,
                ),
                AgentRun(
                    agent_id=agent.id,
                    trigger="schedule",
                    summary="Old fail",
                    status="error",
                    started_at=old_day + timedelta(hours=1),
                    duration_ms=200,
                    tokens_used=20,
                    cost_estimate=0.02,
                ),
                AgentRun(
                    agent_id=agent.id,
                    trigger="manual",
                    summary="Recent",
                    status="success",
                    started_at=recent,
                ),
            ]
        )
        await session.commit()

    async with TestSessionLocal() as session:
        result = await aggregate_old_agent_runs(session, retention_days=90)
        assert result == {"summaries_upserted": 1, "runs_deleted": 2}

    async with TestSessionLocal() as session:
        remaining_runs = (await session.execute(select(AgentRun))).scalars().all()
        summaries = (await session.execute(select(AgentRunDailySummary))).scalars().all()
    assert [run.summary for run in remaining_runs] == ["Recent"]
    assert len(summaries) == 1
    assert summaries[0].run_count == 2
    assert summaries[0].success_count == 1
    assert summaries[0].failure_count == 1
    assert summaries[0].total_duration_ms == 300
    assert summaries[0].total_tokens_used == 30
    assert summaries[0].total_cost_estimate == 0.03
    assert summaries[0].summaries == ["Old ok", "Old fail"]
