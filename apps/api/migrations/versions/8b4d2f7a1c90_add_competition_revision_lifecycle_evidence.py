"""add competition revision and lifecycle evidence

Revision ID: 8b4d2f7a1c90
Revises: 4d8b6e1a3f20
Create Date: 2026-07-12
"""

import sqlalchemy as sa
from alembic import op

revision = "8b4d2f7a1c90"
down_revision = "4d8b6e1a3f20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "competitions" in tables:
        with op.batch_alter_table("competitions") as batch_op:
            batch_op.add_column(sa.Column("lifecycle_reason", sa.Text(), nullable=True))
            batch_op.add_column(
                sa.Column("lifecycle_changed_at", sa.DateTime(timezone=True), nullable=True)
            )
    if "competition_revisions" in tables:
        with op.batch_alter_table("competition_revisions") as batch_op:
            batch_op.add_column(sa.Column("change_reason", sa.Text(), nullable=True))
    if "messages" not in tables:
        return
    message_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("messages")
    }
    if "user_id" not in message_columns:
        return
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(
            sa.Column(
                "competition_id",
                sa.BigInteger(),
                sa.ForeignKey(
                    "competitions.id",
                    name="fk_messages_competition_id_competitions",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("message_type", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=160), nullable=True))
        batch_op.add_column(
            sa.Column("event_occurred_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(batch_op.f("ix_messages_competition_id"), ["competition_id"])
        batch_op.create_index(batch_op.f("ix_messages_message_type"), ["message_type"])
        batch_op.create_unique_constraint("uq_message_user_event", ["user_id", "idempotency_key"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    message_columns = (
        {column["name"] for column in sa.inspect(op.get_bind()).get_columns("messages")}
        if "messages" in tables
        else set()
    )
    if "idempotency_key" in message_columns:
        with op.batch_alter_table("messages") as batch_op:
            batch_op.drop_constraint("uq_message_user_event", type_="unique")
            batch_op.drop_index(batch_op.f("ix_messages_message_type"))
            batch_op.drop_index(batch_op.f("ix_messages_competition_id"))
            batch_op.drop_column("event_occurred_at")
            batch_op.drop_column("idempotency_key")
            batch_op.drop_column("message_type")
            batch_op.drop_column("competition_id")
    if "competition_revisions" in tables:
        with op.batch_alter_table("competition_revisions") as batch_op:
            batch_op.drop_column("change_reason")
    if "competitions" in tables:
        with op.batch_alter_table("competitions") as batch_op:
            batch_op.drop_column("lifecycle_changed_at")
            batch_op.drop_column("lifecycle_reason")
