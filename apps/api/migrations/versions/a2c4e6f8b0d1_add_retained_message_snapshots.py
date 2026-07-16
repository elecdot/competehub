"""add retained message snapshots

Revision ID: a2c4e6f8b0d1
Revises: a64f1b9d2c7e
Create Date: 2026-07-16
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from alembic import op

revision = "a2c4e6f8b0d1"
down_revision = "a64f1b9d2c7e"
branch_labels = None
depends_on = None

SUPPORTED_MESSAGE_TYPES = frozenset(
    {
        "reminder_due",
        "competition_time_changed",
        "competition_cancelled",
        "competition_offline",
    }
)
RETENTION_PERIOD = timedelta(days=365)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "messages" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("messages")}
    if "user_id" not in columns:
        # The repository's legacy create-all marker intentionally owns this schema path.
        return

    backfill = _preflight_and_prepare_backfill(bind)

    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("target_snapshot", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("retained_until", sa.DateTime(timezone=True), nullable=True))

    messages = sa.Table("messages", sa.MetaData(), autoload_with=bind)
    for message_id, values in backfill.items():
        bind.execute(messages.update().where(messages.c.id == message_id).values(**values))

    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "competition_id",
            existing_type=sa.BigInteger(),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "message_type",
            existing_type=sa.String(length=80),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "idempotency_key",
            existing_type=sa.String(length=160),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "event_occurred_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "title",
            existing_type=sa.String(length=255),
            existing_nullable=False,
            new_column_name="title_snapshot",
        )
        batch_op.alter_column(
            "body",
            existing_type=sa.Text(),
            existing_nullable=True,
            new_column_name="body_snapshot",
        )
        batch_op.alter_column(
            "target_snapshot",
            existing_type=sa.JSON(),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "retained_until",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_messages_supported_type",
            "message_type IN ('reminder_due', 'competition_time_changed', "
            "'competition_cancelled', 'competition_offline')",
        )
        batch_op.create_index("ix_messages_retained_until", ["retained_until"], unique=False)
        batch_op.create_index(
            "ix_messages_user_retention_created",
            ["user_id", "retained_until", "created_at", "id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_messages_user_unread_retention",
            ["user_id", "is_read", "retained_until"],
            unique=False,
        )

    _synchronize_messages_sequence(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "messages" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("messages")}
    if "title_snapshot" not in columns:
        return

    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_index("ix_messages_user_unread_retention")
        batch_op.drop_index("ix_messages_user_retention_created")
        batch_op.drop_index("ix_messages_retained_until")
        batch_op.drop_constraint("ck_messages_supported_type", type_="check")
        batch_op.alter_column(
            "competition_id",
            existing_type=sa.BigInteger(),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "message_type",
            existing_type=sa.String(length=80),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "idempotency_key",
            existing_type=sa.String(length=160),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "event_occurred_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "title_snapshot",
            existing_type=sa.String(length=255),
            existing_nullable=False,
            new_column_name="title",
        )
        batch_op.alter_column(
            "body_snapshot",
            existing_type=sa.Text(),
            existing_nullable=True,
            new_column_name="body",
        )
        batch_op.drop_column("retained_until")
        batch_op.drop_column("target_snapshot")


def _preflight_and_prepare_backfill(bind) -> dict[int, dict]:
    metadata = sa.MetaData()
    table_names = set(sa.inspect(bind).get_table_names())
    required_tables = {"users", "competitions", "messages"}
    missing_tables = required_tables - table_names
    if missing_tables:
        raise RuntimeError(
            "Cannot migrate retained messages because required tables are missing: "
            + ", ".join(sorted(missing_tables))
        )
    reflected = ["users", "competitions", "messages"]
    if "reminders" in table_names:
        reflected.append("reminders")
    if "competition_time_nodes" in table_names:
        reflected.append("competition_time_nodes")
    if "competition_revisions" in table_names:
        reflected.append("competition_revisions")
    metadata.reflect(bind=bind, only=reflected)

    users = metadata.tables["users"]
    competitions = metadata.tables["competitions"]
    messages = metadata.tables["messages"]
    reminders = metadata.tables.get("reminders")
    time_nodes = metadata.tables.get("competition_time_nodes")
    revisions = metadata.tables.get("competition_revisions")

    user_ids = set(bind.execute(sa.select(users.c.id)).scalars())
    competition_rows = {row["id"]: row for row in bind.execute(sa.select(competitions)).mappings()}
    reminder_rows = (
        {row["id"]: row for row in bind.execute(sa.select(reminders)).mappings()}
        if reminders is not None
        else {}
    )
    time_node_rows = (
        {row["id"]: row for row in bind.execute(sa.select(time_nodes)).mappings()}
        if time_nodes is not None
        else {}
    )
    revision_rows = (
        {row["id"]: row for row in bind.execute(sa.select(revisions)).mappings()}
        if revisions is not None
        else {}
    )

    prepared: dict[int, dict] = {}
    seen_keys: set[tuple[int, str]] = set()
    failures: list[str] = []
    for message in bind.execute(sa.select(messages).order_by(messages.c.id)).mappings():
        message_id = message["id"]
        user_id = message["user_id"]
        reminder = reminder_rows.get(message["reminder_id"])
        competition_id = message["competition_id"] or (
            reminder["competition_id"] if reminder is not None else None
        )
        message_type = message["message_type"] or ("reminder_due" if reminder is not None else None)
        idempotency_key = message["idempotency_key"] or f"legacy-message:{message_id}"
        reminder_due_at = reminder["due_at"] if reminder is not None else None
        event_occurred_at = message["event_occurred_at"] or reminder_due_at or message["created_at"]
        competition = competition_rows.get(competition_id)

        row_failures = []
        if user_id not in user_ids:
            row_failures.append("user_id")
        if competition is None:
            row_failures.append("competition_id")
        if message_type not in SUPPORTED_MESSAGE_TYPES:
            row_failures.append("message_type")
        if event_occurred_at is None:
            row_failures.append("event_occurred_at")
        if message["created_at"] is None:
            row_failures.append("created_at")
        if (user_id, idempotency_key) in seen_keys:
            row_failures.append("idempotency_key")
        if message["reminder_id"] is not None and reminder is None:
            row_failures.append("reminder_id")
        if message_type == "reminder_due" and reminder is None:
            row_failures.append("reminder_due.reminder_id")
        if reminder is not None:
            if message_type == "reminder_due":
                if reminder["status"] != "sent":
                    row_failures.append("reminder.status")
                if (reminder["attempt_count"] or 0) <= 0:
                    row_failures.append("reminder.attempt_count")
                if reminder["sent_at"] is None:
                    row_failures.append("reminder.sent_at")
            else:
                row_failures.append("non_reminder_due.reminder_id")
            if reminder["user_id"] != user_id:
                row_failures.append("reminder.user_id")
            if (
                message["competition_id"] is not None
                and message["competition_id"] != reminder["competition_id"]
            ):
                row_failures.append("reminder.competition_id")

        node_type = None
        node_occurs_at = None
        if reminder is not None:
            node_type = reminder["node_type"]
            time_node = time_node_rows.get(reminder["time_node_snapshot_id"])
            node_occurs_at = time_node["occurs_at"] if time_node is not None else None
            if not node_type:
                row_failures.append("reminder.node_type")
            if time_node is None or node_occurs_at is None:
                row_failures.append("reminder.time_node_snapshot")
            elif _time_node_competition_id(time_node, revision_rows) != competition_id:
                row_failures.append("time_node.competition_id")

        if row_failures:
            failures.append(f"message {message_id}: {', '.join(row_failures)}")
            continue

        seen_keys.add((user_id, idempotency_key))
        prepared[message_id] = {
            "competition_id": competition_id,
            "message_type": message_type,
            "idempotency_key": idempotency_key,
            "event_occurred_at": event_occurred_at,
            "target_snapshot": {
                "competition_id": competition_id,
                "competition_title": competition["title"],
                "node_type": node_type,
                "node_occurs_at": _snapshot_datetime(node_occurs_at),
                "reason_summary": _lifecycle_reason(message_type, message, competition),
            },
            "retained_until": message["created_at"] + RETENTION_PERIOD,
        }

    if failures:
        raise RuntimeError(
            "Cannot migrate retained messages; preflight could not derive required facts ("
            + "; ".join(failures)
            + "). No message schema changes were applied."
        )
    return prepared


def _synchronize_messages_sequence(bind) -> None:
    """Advance PostgreSQL's generated ID past every preserved legacy message."""
    if bind.dialect.name != "postgresql":
        return
    bind.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('messages', 'id'),
                COALESCE((SELECT max(id) FROM messages), 1),
                (SELECT count(*) > 0 FROM messages)
            )
            """
        )
    )


def _snapshot_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _time_node_competition_id(time_node, revision_rows: dict[int, object]) -> int | None:
    if time_node["competition_id"] is not None:
        return time_node["competition_id"]
    revision = revision_rows.get(time_node["competition_revision_id"])
    return revision["competition_id"] if revision is not None else None


def _lifecycle_reason(message_type: str, message, competition) -> str | None:
    if message_type not in {"competition_cancelled", "competition_offline"}:
        return None
    # Issue #37 wrote the event-local lifecycle reason into the legacy body.
    # Current competition state may describe a later offline/cancellation episode.
    if message["body"] is not None:
        return message["body"]
    expected_type = f"competition_{competition['status']}"
    if (
        message_type == expected_type
        and message["event_occurred_at"] is not None
        and competition.get("lifecycle_changed_at") == message["event_occurred_at"]
    ):
        return competition.get("lifecycle_reason")
    return None
