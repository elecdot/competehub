"""add outbound click analytics

Revision ID: a64f1b9d2c7e
Revises: 13eb10903bd7
Create Date: 2026-07-12 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "a64f1b9d2c7e"
down_revision = "13eb10903bd7"
branch_labels = None
depends_on = None

BIGINT_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "outbound_click_events",
        sa.Column("id", BIGINT_PK, primary_key=True),
        sa.Column("competition_id", BIGINT_PK, nullable=False),
        sa.Column("competition_revision_id", BIGINT_PK, nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("source_surface", sa.String(length=32), nullable=False),
        sa.Column("actor_kind", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"]),
        sa.ForeignKeyConstraint(["competition_revision_id"], ["competition_revisions.id"]),
    )
    op.create_index(
        "ix_outbound_click_events_competition_id", "outbound_click_events", ["competition_id"]
    )
    op.create_index(
        "ix_outbound_click_events_competition_revision_id",
        "outbound_click_events",
        ["competition_revision_id"],
    )
    op.create_index(
        "ix_outbound_click_events_occurred_at", "outbound_click_events", ["occurred_at"]
    )
    op.create_table(
        "outbound_click_daily_stats",
        sa.Column("id", BIGINT_PK, primary_key=True),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("competition_id", BIGINT_PK, nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("source_surface", sa.String(length=32), nullable=False),
        sa.Column("actor_kind", sa.String(length=32), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"]),
        sa.UniqueConstraint(
            "stat_date",
            "competition_id",
            "target_type",
            "source_surface",
            "actor_kind",
            name="uq_outbound_click_daily_stat_dimensions",
        ),
    )
    op.create_index(
        "ix_outbound_click_daily_stats_stat_date", "outbound_click_daily_stats", ["stat_date"]
    )
    op.create_index(
        "ix_outbound_click_daily_stats_competition_id",
        "outbound_click_daily_stats",
        ["competition_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbound_click_daily_stats_competition_id",
        table_name="outbound_click_daily_stats",
    )
    op.drop_index(
        "ix_outbound_click_daily_stats_stat_date",
        table_name="outbound_click_daily_stats",
    )
    op.drop_table("outbound_click_daily_stats")
    op.drop_index("ix_outbound_click_events_occurred_at", table_name="outbound_click_events")
    op.drop_index(
        "ix_outbound_click_events_competition_revision_id",
        table_name="outbound_click_events",
    )
    op.drop_index(
        "ix_outbound_click_events_competition_id",
        table_name="outbound_click_events",
    )
    op.drop_table("outbound_click_events")
