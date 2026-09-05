"""add challenges and check ins

Revision ID: a5c2f91e6b37
Revises: d4b8f72c9e11
Create Date: 2026-09-05 13:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a5c2f91e6b37"
down_revision: str | None = "d4b8f72c9e11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("vision_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_days", sa.Integer(), nullable=True),
        sa.Column("allowed_gap_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("color", sa.String(length=7), nullable=False, server_default="#22c55e"),
        sa.Column("icon", sa.String(length=80), nullable=False, server_default="activity"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vision_id"], ["visions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_challenges_category_id"), "challenges", ["category_id"], unique=False)
    op.create_index(op.f("ix_challenges_is_active"), "challenges", ["is_active"], unique=False)
    op.create_index(op.f("ix_challenges_owner_id"), "challenges", ["owner_id"], unique=False)
    op.create_index(op.f("ix_challenges_type"), "challenges", ["type"], unique=False)
    op.create_index(op.f("ix_challenges_vision_id"), "challenges", ["vision_id"], unique=False)

    op.create_table(
        "check_ins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(12, 3), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_relapse", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id", "date", name="uq_check_ins_challenge_date"),
    )
    op.create_index(op.f("ix_check_ins_challenge_id"), "check_ins", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_check_ins_date"), "check_ins", ["date"], unique=False)
    op.create_index(op.f("ix_check_ins_is_relapse"), "check_ins", ["is_relapse"], unique=False)
    op.create_index(op.f("ix_check_ins_owner_id"), "check_ins", ["owner_id"], unique=False)

    op.create_table(
        "challenge_pauses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_challenge_pauses_challenge_id"), "challenge_pauses", ["challenge_id"], unique=False
    )
    op.create_index(
        op.f("ix_challenge_pauses_owner_id"), "challenge_pauses", ["owner_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_challenge_pauses_owner_id"), table_name="challenge_pauses")
    op.drop_index(op.f("ix_challenge_pauses_challenge_id"), table_name="challenge_pauses")
    op.drop_table("challenge_pauses")
    op.drop_index(op.f("ix_check_ins_owner_id"), table_name="check_ins")
    op.drop_index(op.f("ix_check_ins_is_relapse"), table_name="check_ins")
    op.drop_index(op.f("ix_check_ins_date"), table_name="check_ins")
    op.drop_index(op.f("ix_check_ins_challenge_id"), table_name="check_ins")
    op.drop_table("check_ins")
    op.drop_index(op.f("ix_challenges_vision_id"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_type"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_owner_id"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_is_active"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_category_id"), table_name="challenges")
    op.drop_table("challenges")
