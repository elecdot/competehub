"""add student following and reminder integrity

Revision ID: 7f3c2a91d8e4
Revises: 13eb10903bd7
Create Date: 2026-07-12 18:00:00
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7f3c2a91d8e4"
down_revision = "13eb10903bd7"
branch_labels = None
depends_on = None

BASELINE_TABLE = "competehub_migration_baselines"
BASELINE_KEY = "c5e0e7e0560d.schema_path"
SCHEMA_PATH_LEGACY = "legacy_create_all"
ENGAGEMENT_TABLES = ("favorites", "subscriptions", "reminders")
DEFAULT_NODE_TYPES = [
    "registration_deadline",
    "submission_deadline",
    "competition_start",
]


def upgrade():
    if _schema_path() == SCHEMA_PATH_LEGACY:
        return

    _refuse_nonempty_engagement("upgrade")
    _backfill_reminder_settings()
    _synchronize_reminder_settings_sequence()
    _upgrade_engagement_schema()
    _drop_profile_reminder_columns()


def downgrade():
    if _schema_path() == SCHEMA_PATH_LEGACY:
        return

    _refuse_nonempty_engagement("downgrade")
    _restore_profile_reminder_columns()
    _downgrade_engagement_schema()


def _refuse_nonempty_engagement(direction: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    counts = {
        table_name: bind.execute(sa.text(f"SELECT count(*) FROM {table_name}")).scalar_one()
        for table_name in ENGAGEMENT_TABLES
        if table_name in existing_tables
    }
    populated = {table_name: count for table_name, count in counts.items() if count}
    if not populated:
        return

    count_summary = ", ".join(
        f"{table_name}={populated[table_name]}"
        for table_name in ENGAGEMENT_TABLES
        if table_name in populated
    )
    action = "bridge before upgrading" if direction == "upgrade" else "safe downgrade policy"
    raise RuntimeError(
        f"Cannot {direction} Issue #38 engagement schema with retained rows "
        f"({count_summary}). Reset a disposable database or provide a separately reviewed {action}."
    )


def _backfill_reminder_settings() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    metadata.reflect(bind=bind, only=["users", "student_profiles", "reminder_settings"])
    users = metadata.tables["users"]
    profiles = metadata.tables["student_profiles"]
    settings = metadata.tables["reminder_settings"]

    existing_user_ids = set(bind.execute(sa.select(settings.c.user_id)).scalars())
    profiles_by_user_id = {
        row["user_id"]: row for row in bind.execute(sa.select(profiles)).mappings()
    }
    next_setting_id = (bind.execute(sa.select(sa.func.max(settings.c.id))).scalar() or 0) + 1
    now = datetime.now(UTC)
    rows = []
    student_ids = bind.execute(
        sa.select(users.c.id).where(users.c.role == "student").order_by(users.c.id)
    ).scalars()
    for user_id in student_ids:
        if user_id in existing_user_ids:
            continue
        profile = profiles_by_user_id.get(user_id)
        rows.append(
            {
                "id": next_setting_id,
                "user_id": user_id,
                "enabled": profile["message_enabled"] if profile is not None else True,
                "default_remind_days": (
                    profile["default_remind_days"] if profile is not None else 3
                ),
                "node_types": list(DEFAULT_NODE_TYPES),
                "created_at": now,
                "updated_at": now,
            }
        )
        next_setting_id += 1
    if rows:
        bind.execute(settings.insert(), rows)


def _synchronize_reminder_settings_sequence() -> None:
    """Advance PostgreSQL's generated-id sequence after explicit backfill ids."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    bind.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('reminder_settings', 'id'),
                COALESCE((SELECT max(id) FROM reminder_settings), 1),
                (SELECT count(*) > 0 FROM reminder_settings)
            )
            """
        )
    )


def _upgrade_engagement_schema() -> None:
    with op.batch_alter_table("favorites", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_favorites_user_competition",
            ["user_id", "competition_id"],
        )

    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reminder_confirmed_at", sa.DateTime(timezone=True)))
        batch_op.create_unique_constraint(
            "uq_subscriptions_user_competition",
            ["user_id", "competition_id"],
        )
        batch_op.create_check_constraint(
            "ck_subscriptions_remind_days_range",
            "remind_days >= 0 AND remind_days <= 30",
        )

    with op.batch_alter_table("reminders", schema=None) as batch_op:
        batch_op.alter_column(
            "time_node_id",
            existing_type=sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            new_column_name="time_node_snapshot_id",
            existing_nullable=True,
            nullable=False,
        )
        batch_op.add_column(sa.Column("logical_node_key", sa.String(length=120), nullable=False))
        batch_op.add_column(sa.Column("time_node_revision", sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column("cancel_reason", sa.String(length=80)))
        batch_op.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("last_error_code", sa.String(length=80)))
        batch_op.add_column(sa.Column("failed_at", sa.DateTime(timezone=True)))
        batch_op.create_unique_constraint(
            "uq_reminders_ordinary_plan",
            ["user_id", "competition_id", "logical_node_key", "time_node_revision"],
        )


def _drop_profile_reminder_columns() -> None:
    with op.batch_alter_table("student_profiles", schema=None) as batch_op:
        batch_op.drop_column("message_enabled")
        batch_op.drop_column("default_remind_days")


def _restore_profile_reminder_columns() -> None:
    with op.batch_alter_table("student_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("default_remind_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("message_enabled", sa.Boolean(), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE student_profiles
            SET default_remind_days = (
                    SELECT reminder_settings.default_remind_days
                    FROM reminder_settings
                    WHERE reminder_settings.user_id = student_profiles.user_id
                ),
                message_enabled = (
                    SELECT reminder_settings.enabled
                    FROM reminder_settings
                    WHERE reminder_settings.user_id = student_profiles.user_id
                )
            """
        )
    )
    missing = bind.execute(
        sa.text(
            """
            SELECT count(*) FROM student_profiles
            WHERE default_remind_days IS NULL OR message_enabled IS NULL
            """
        )
    ).scalar_one()
    if missing:
        raise RuntimeError(
            "Cannot restore legacy profile reminder columns because one or more student profiles "
            "lack authoritative reminder_settings rows."
        )
    with op.batch_alter_table("student_profiles", schema=None) as batch_op:
        batch_op.alter_column("default_remind_days", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("message_enabled", existing_type=sa.Boolean(), nullable=False)


def _downgrade_engagement_schema() -> None:
    with op.batch_alter_table("reminders", schema=None) as batch_op:
        batch_op.drop_constraint("uq_reminders_ordinary_plan", type_="unique")
        batch_op.drop_column("failed_at")
        batch_op.drop_column("last_error_code")
        batch_op.drop_column("next_attempt_at")
        batch_op.drop_column("attempt_count")
        batch_op.drop_column("cancel_reason")
        batch_op.drop_column("time_node_revision")
        batch_op.drop_column("logical_node_key")
        batch_op.alter_column(
            "time_node_snapshot_id",
            existing_type=sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            new_column_name="time_node_id",
            existing_nullable=False,
            nullable=True,
        )

    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.drop_constraint("ck_subscriptions_remind_days_range", type_="check")
        batch_op.drop_constraint("uq_subscriptions_user_competition", type_="unique")
        batch_op.drop_column("reminder_confirmed_at")

    with op.batch_alter_table("favorites", schema=None) as batch_op:
        batch_op.drop_constraint("uq_favorites_user_competition", type_="unique")


def _schema_path():
    bind = op.get_bind()
    if BASELINE_TABLE not in sa.inspect(bind).get_table_names():
        return None
    return bind.execute(
        sa.text(f"SELECT value FROM {BASELINE_TABLE} WHERE key = :key"),
        {"key": BASELINE_KEY},
    ).scalar()
