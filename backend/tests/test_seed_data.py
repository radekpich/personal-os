import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_phase2_seed_migration_creates_demo_owner_categories_contexts_and_tasks(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "seed.db"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
            "SECRET_KEY": "seed-test-secret-key-for-local-test-only",
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
    )

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=".",
        env=env,
        check=False,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    with sqlite3.connect(db_path) as conn:
        categories = {row[0] for row in conn.execute("select name from categories")}
        contexts = {row[0] for row in conn.execute("select name from contexts")}
        tasks = {
            row[0]: row[1:]
            for row in conn.execute(
                "select title, recurrence_rule, recurrence_mode from tasks order by title"
            )
        }
        demo_user = conn.execute(
            "select email, is_active from users where email = 'seed-demo@personal-os.local'"
        ).fetchone()

    assert demo_user == ("seed-demo@personal-os.local", 0)
    assert categories == {
        "KEXO",
        "Ranč na Valech",
        "Stavba",
        "Hospodářství",
        "Rodina",
        "Kondice",
    }
    assert contexts == {"@ranč", "@Staré Buky", "@počítač", "@telefon", "@město"}
    assert "Zkontrolovat zdivo a rozvody" in tasks
    assert tasks["Krmení zvířat"] == ("FREQ=DAILY;INTERVAL=1", "fixed")
