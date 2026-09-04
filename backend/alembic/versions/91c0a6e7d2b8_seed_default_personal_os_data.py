"""seed default personal os data

Revision ID: 91c0a6e7d2b8
Revises: 7b1d2c5e9f40
Create Date: 2026-09-04 21:00:00.000000

"""

from collections.abc import Sequence
from datetime import date, time
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "91c0a6e7d2b8"
down_revision: str | None = "7b1d2c5e9f40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
CATEGORY_IDS = {
    "Ranč na Valech": UUID("20000000-0000-4000-8000-000000000001"),
    "KEXO": UUID("20000000-0000-4000-8000-000000000002"),
    "Stavba": UUID("20000000-0000-4000-8000-000000000003"),
    "Hospodářství": UUID("20000000-0000-4000-8000-000000000004"),
    "Rodina": UUID("20000000-0000-4000-8000-000000000005"),
    "Kondice": UUID("20000000-0000-4000-8000-000000000006"),
}
CONTEXT_IDS = {
    "@ranč": UUID("30000000-0000-4000-8000-000000000001"),
    "@Staré Buky": UUID("30000000-0000-4000-8000-000000000002"),
    "@počítač": UUID("30000000-0000-4000-8000-000000000003"),
    "@telefon": UUID("30000000-0000-4000-8000-000000000004"),
    "@město": UUID("30000000-0000-4000-8000-000000000005"),
}
TASK_IDS = {
    "Krmení zvířat": UUID("40000000-0000-4000-8000-000000000001"),
    "Zkontrolovat zdivo a rozvody": UUID("40000000-0000-4000-8000-000000000002"),
    "Připravit nabídku pro svatbu": UUID("40000000-0000-4000-8000-000000000003"),
}


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "users",
            sa.column("id", sa.Uuid()),
            sa.column("email", sa.String()),
            sa.column("hashed_password", sa.String()),
            sa.column("display_name", sa.String()),
            sa.column("timezone", sa.String()),
            sa.column("calendar_token", sa.String()),
            sa.column("is_active", sa.Boolean()),
        ),
        [
            {
                "id": DEMO_USER_ID,
                "email": "seed-demo@personal-os.local",
                "hashed_password": "disabled-seed-user-no-login",
                "display_name": "Seed Demo",
                "timezone": "Europe/Prague",
                "calendar_token": "seed-demo-calendar-token-do-not-use",
                "is_active": False,
            }
        ],
    )
    category_rows = [
        {
            "id": category_id,
            "owner_id": DEMO_USER_ID,
            "name": name,
            "color": color,
            "icon": icon,
            "position": position,
            "is_archived": False,
        }
        for position, (name, category_id, color, icon) in enumerate(
            [
                ("Ranč na Valech", CATEGORY_IDS["Ranč na Valech"], "#8B5E3C", "barn"),
                ("KEXO", CATEGORY_IDS["KEXO"], "#0EA5E9", "briefcase"),
                ("Stavba", CATEGORY_IDS["Stavba"], "#F59E0B", "home"),
                ("Hospodářství", CATEGORY_IDS["Hospodářství"], "#22C55E", "tractor"),
                ("Rodina", CATEGORY_IDS["Rodina"], "#EC4899", "heart"),
                ("Kondice", CATEGORY_IDS["Kondice"], "#6366F1", "activity"),
            ]
        )
    ]
    op.bulk_insert(
        sa.table(
            "categories",
            sa.column("id", sa.Uuid()),
            sa.column("owner_id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("color", sa.String()),
            sa.column("icon", sa.String()),
            sa.column("position", sa.Integer()),
            sa.column("is_archived", sa.Boolean()),
        ),
        category_rows,
    )
    context_rows = [
        {
            "id": context_id,
            "owner_id": DEMO_USER_ID,
            "name": name,
            "position": position,
            "is_archived": False,
        }
        for position, (name, context_id) in enumerate(CONTEXT_IDS.items())
    ]
    op.bulk_insert(
        sa.table(
            "contexts",
            sa.column("id", sa.Uuid()),
            sa.column("owner_id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("position", sa.Integer()),
            sa.column("is_archived", sa.Boolean()),
        ),
        context_rows,
    )
    task_rows = [
        {
            "id": TASK_IDS["Krmení zvířat"],
            "owner_id": DEMO_USER_ID,
            "title": "Krmení zvířat",
            "status": "todo",
            "priority": "medium",
            "due_date": date(2026, 9, 5),
            "due_time": time(8, 0),
            "category_id": CATEGORY_IDS["Hospodářství"],
            "context_id": CONTEXT_IDS["@ranč"],
            "recurrence_rule": "FREQ=DAILY;INTERVAL=1",
            "recurrence_mode": "fixed",
            "position": 0,
        },
        {
            "id": TASK_IDS["Zkontrolovat zdivo a rozvody"],
            "owner_id": DEMO_USER_ID,
            "title": "Zkontrolovat zdivo a rozvody",
            "status": "todo",
            "priority": "high",
            "due_date": date(2026, 9, 7),
            "due_time": None,
            "category_id": CATEGORY_IDS["Stavba"],
            "context_id": CONTEXT_IDS["@Staré Buky"],
            "recurrence_rule": None,
            "recurrence_mode": None,
            "position": 1,
        },
        {
            "id": TASK_IDS["Připravit nabídku pro svatbu"],
            "owner_id": DEMO_USER_ID,
            "title": "Připravit nabídku pro svatbu",
            "status": "todo",
            "priority": "high",
            "due_date": date(2026, 9, 8),
            "due_time": None,
            "category_id": CATEGORY_IDS["Ranč na Valech"],
            "context_id": CONTEXT_IDS["@počítač"],
            "recurrence_rule": None,
            "recurrence_mode": None,
            "position": 2,
        },
    ]
    op.bulk_insert(
        sa.table(
            "tasks",
            sa.column("id", sa.Uuid()),
            sa.column("owner_id", sa.Uuid()),
            sa.column("title", sa.String()),
            sa.column("status", sa.String()),
            sa.column("priority", sa.String()),
            sa.column("due_date", sa.Date()),
            sa.column("due_time", sa.Time()),
            sa.column("category_id", sa.Uuid()),
            sa.column("context_id", sa.Uuid()),
            sa.column("recurrence_rule", sa.String()),
            sa.column("recurrence_mode", sa.String()),
            sa.column("position", sa.Integer()),
        ),
        task_rows,
    )


def downgrade() -> None:
    owner_sql = "(SELECT id FROM users WHERE email = 'seed-demo@personal-os.local')"
    op.execute(f"DELETE FROM tasks WHERE owner_id = {owner_sql}")
    op.execute(f"DELETE FROM contexts WHERE owner_id = {owner_sql}")
    op.execute(f"DELETE FROM categories WHERE owner_id = {owner_sql}")
    op.execute("DELETE FROM users WHERE email = 'seed-demo@personal-os.local'")
