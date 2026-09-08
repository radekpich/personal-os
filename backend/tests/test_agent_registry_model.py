import os
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.models.agent_registry import (
    AgentChannel,
    AgentConfigChange,
    AgentInstance,
    AgentIntegration,
    AgentJob,
    AgentRun,
    AgentRunDailySummary,
    AgentWatch,
)
from tests.conftest import TestSessionLocal


async def test_agent_registry_models_roundtrip(setup_db: None) -> None:
    now = datetime.now(UTC)
    async with TestSessionLocal() as db_session:
        agent = AgentInstance(
            owner_id=uuid.uuid4(),
            name="hermes",
            version="1.2.3",
            host="ranch-vps",
            started_at=now,
            last_heartbeat_at=now,
            status="running",
            config_hash="hash-a",
        )
        db_session.add(agent)
        await db_session.flush()

        job = AgentJob(
            agent_id=agent.id,
            name="daily briefing",
            description="Morning brief",
            schedule="0 7 * * *",
            schedule_description="každý den v 7:00",
            is_enabled=True,
            next_run_at=now + timedelta(hours=1),
            last_status="success",
            last_duration_ms=321,
            consecutive_failures=0,
            run_count=42,
            tags=["briefing", "telegram"],
        )
        integration = AgentIntegration(
            agent_id=agent.id,
            name="Google Calendar",
            kind="calendar",
            scopes=["calendar.read", "calendar.write"],
            status="active",
            last_used_at=now,
            error_count=0,
            notes="OAuth configured; no token stored",
        )
        watch = AgentWatch(
            agent_id=agent.id,
            name="disk watchdog",
            description="Warns about disk pressure",
            kind="system",
            config_json={"threshold_percent": 85},
            schedule="*/30 * * * *",
            is_active=True,
            last_result="ok",
        )
        channel = AgentChannel(
            agent_id=agent.id,
            channel_type="telegram",
            identifier="Home",
            is_active=True,
            message_count_24h=5,
            message_count_month=120,
        )
        run = AgentRun(
            agent_id=agent.id,
            job=job,
            trigger="schedule",
            summary="Sent daily briefing.",
            detail="Delivered to Telegram.",
            status="success",
            started_at=now,
            finished_at=now + timedelta(milliseconds=321),
            duration_ms=321,
            tokens_used=1234,
            cost_estimate=0.0123,
            tags=["briefing"],
        )
        change = AgentConfigChange(
            agent_id=agent.id,
            change_type="added",
            target_type="integration",
            target_name="Google Calendar",
            diff_json={"after": {"kind": "calendar"}},
        )
        summary = AgentRunDailySummary(
            agent_id=agent.id,
            day=now.date(),
            run_count=7,
            success_count=6,
            failure_count=1,
            total_duration_ms=999,
            total_tokens_used=5000,
            total_cost_estimate=0.1,
            summaries=["Daily aggregate"],
        )
        db_session.add_all([job, integration, watch, channel, run, change, summary])
        await db_session.commit()

        loaded = (
            await db_session.execute(select(AgentInstance).where(AgentInstance.name == "hermes"))
        ).scalar_one()
        assert loaded.jobs[0].schedule_description == "každý den v 7:00"
        assert loaded.integrations[0].scopes == ["calendar.read", "calendar.write"]
        assert loaded.watches[0].config_json == {"threshold_percent": 85}
        assert loaded.channels[0].message_count_month == 120
        assert loaded.runs[0].summary == "Sent daily briefing."
        assert loaded.config_changes[0].acknowledged_at is None


def test_agent_registry_alembic_tables_exist(tmp_path: Path) -> None:
    database_path = tmp_path / "registry.sqlite"
    env = os.environ | {
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
        "SECRET_KEY": "test-secret-key-for-registry-migration",
        "CORS_ORIGINS": "https://testserver",
        "COOKIE_SECURE": "true",
        "ENVIRONMENT": "test",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "REFRESH_TOKEN_EXPIRE_DAYS": "30",
        "ACCESS_COOKIE_NAME": "access_token",
        "REFRESH_COOKIE_NAME": "refresh_token",
        "CSRF_COOKIE_NAME": "csrf_token",
        "CSRF_HEADER_NAME": "X-CSRF-Token",
        "RATE_LIMIT_LOGIN": "5/minute",
        "RATE_LIMIT_DEFAULT": "1000/minute",
    }
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    import sqlite3

    with sqlite3.connect(database_path) as conn:
        table_names = {
            row[0] for row in conn.execute("select name from sqlite_master where type='table'")
        }
    assert {
        "agent_instances",
        "agent_jobs",
        "agent_integrations",
        "agent_watches",
        "agent_channels",
        "agent_capabilities",
        "agent_runs",
        "agent_config_changes",
        "agent_run_daily_summaries",
    }.issubset(table_names)
