import asyncio
from typing import Any

from pytest import MonkeyPatch

from app.core.config import Settings
from app.services.calendar_writer_trigger import trigger_calendar_writer


def _settings(command: str | None) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=30,
        cors_origins="http://localhost:3000",
        cookie_secure=False,
        access_cookie_name="access_token",
        refresh_cookie_name="refresh_token",
        csrf_cookie_name="csrf_token",
        csrf_header_name="X-CSRF-Token",
        rate_limit_login="100/minute",
        rate_limit_default="100/minute",
        environment="test",
        calendar_writer_trigger_command=command,
    )


async def test_calendar_writer_trigger_is_noop_without_command(monkeypatch: MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_create_subprocess_shell(*args: object, **kwargs: object) -> None:
        calls.append(str(args[0]))
        raise AssertionError("trigger should not start without a command")

    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_create_subprocess_shell)

    await trigger_calendar_writer(_settings(None))

    assert calls == []


async def test_calendar_writer_trigger_runs_configured_command(monkeypatch: MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def fake_create_subprocess_shell(command: str, **kwargs: Any) -> FakeProcess:
        calls.append(command)
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        assert kwargs["stderr"] == asyncio.subprocess.PIPE
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_create_subprocess_shell)

    await trigger_calendar_writer(_settings("/bin/true"))

    assert calls == ["/bin/true"]
