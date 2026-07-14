"""add recommendation rule-set governance

Revision ID: be7dfc45f976
Revises: 13eb10903bd7
Create Date: 2026-07-11 14:39:49.692143

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "be7dfc45f976"
down_revision = "13eb10903bd7"
branch_labels = None
depends_on = None

RULE_SET_STATUS = sa.Enum(
    "draft",
    "pending_review",
    "active",
    "rejected",
    "returned",
    "retired",
    name="recommendation_rule_set_status",
)


def upgrade():
    # Pre-governance rule rows were mutable and had no reviewed version identity,
    # so they cannot be promoted into an active immutable rule set implicitly.
    existing_rule_count = (
        op.get_bind().execute(sa.text("SELECT COUNT(*) FROM recommendation_rules")).scalar_one()
    )
    if existing_rule_count:
        raise RuntimeError(
            "refusing recommendation rule-set governance migration because the legacy mutable "
            "recommendation_rules table is populated; no legacy rule may be discarded or "
            "promoted automatically. Back up the database and make an explicit, reviewed data "
            "migration decision before retrying"
        )
    op.drop_table("recommendation_rules")

    op.create_table(
        "recommendation_rule_sets",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", RULE_SET_STATUS, nullable=False),
        sa.Column(
            "created_by_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True
        ),
        sa.Column(
            "submitted_by_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True
        ),
        sa.Column(
            "reviewed_by_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True
        ),
        sa.Column(
            "cloned_from_rule_set_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "base_rule_set_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True
        ),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "version >= 1", name=op.f("ck_recommendation_rule_sets_version_positive")
        ),
        sa.ForeignKeyConstraint(
            ["base_rule_set_id"],
            ["recommendation_rule_sets.id"],
            name=op.f("fk_recommendation_rule_sets_base_rule_set_id_recommendation_rule_sets"),
        ),
        sa.ForeignKeyConstraint(
            ["cloned_from_rule_set_id"],
            ["recommendation_rule_sets.id"],
            name=op.f(
                "fk_recommendation_rule_sets_cloned_from_rule_set_id_recommendation_rule_sets"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_recommendation_rule_sets_created_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"],
            ["users.id"],
            name=op.f("fk_recommendation_rule_sets_reviewed_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_id"],
            ["users.id"],
            name=op.f("fk_recommendation_rule_sets_submitted_by_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_rule_sets")),
        sa.UniqueConstraint("version", name=op.f("uq_recommendation_rule_sets_version")),
    )
    with op.batch_alter_table("recommendation_rule_sets", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_recommendation_rule_sets_status"), ["status"], unique=False
        )
        batch_op.create_index(
            "uq_recommendation_rule_sets_active",
            ["status"],
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
            sqlite_where=sa.text("status = 'active'"),
        )

    op.create_table(
        "recommendation_rules",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column(
            "rule_set_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("reason_template", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "weight >= 1 AND weight <= 100",
            name=op.f("ck_recommendation_rules_weight_range"),
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["recommendation_rule_sets.id"],
            name=op.f("fk_recommendation_rules_rule_set_id_recommendation_rule_sets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_rules")),
        sa.UniqueConstraint(
            "rule_set_id",
            "code",
            name=op.f("uq_recommendation_rules_rule_set_code"),
        ),
    )

    review_columns = _column_names("review_records")
    review_columns_to_add = [
        column
        for column in (
            sa.Column("target_revision", sa.Integer(), nullable=True),
            sa.Column("difference_snapshot", sa.JSON(), nullable=True),
            sa.Column("impact_summary", sa.JSON(), nullable=True),
        )
        if column.name not in review_columns
    ]
    if review_columns_to_add:
        with op.batch_alter_table("review_records", schema=None) as batch_op:
            for column in review_columns_to_add:
                batch_op.add_column(column)

    review_columns = _column_names("review_records")
    if {"target_type", "target_id", "target_revision"} <= review_columns and not _has_unique(
        "review_records", "uq_review_records_target_version"
    ):
        with op.batch_alter_table("review_records", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_review_records_target_version",
                ["target_type", "target_id", "target_revision"],
            )


def downgrade():
    if _has_unique("review_records", "uq_review_records_target_version"):
        with op.batch_alter_table("review_records", schema=None) as batch_op:
            batch_op.drop_constraint("uq_review_records_target_version", type_="unique")

    review_columns = _column_names("review_records")
    review_columns_to_drop = [
        column_name
        for column_name in (
            "impact_summary",
            "difference_snapshot",
            "target_revision",
        )
        if column_name in review_columns
    ]
    if review_columns_to_drop:
        with op.batch_alter_table("review_records", schema=None) as batch_op:
            for column_name in review_columns_to_drop:
                batch_op.drop_column(column_name)

    op.drop_table("recommendation_rules")
    with op.batch_alter_table("recommendation_rule_sets", schema=None) as batch_op:
        batch_op.drop_index("uq_recommendation_rule_sets_active")
        batch_op.drop_index(batch_op.f("ix_recommendation_rule_sets_status"))
    op.drop_table("recommendation_rule_sets")

    if op.get_bind().dialect.name == "postgresql":
        RULE_SET_STATUS.drop(op.get_bind(), checkfirst=True)

    op.create_table(
        "recommendation_rules",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("reason_template", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_rules")),
        sa.UniqueConstraint("code", name=op.f("uq_recommendation_rules_code")),
    )


def _column_names(table_name):
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _has_unique(table_name, constraint_name):
    return any(
        constraint["name"] == constraint_name
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table_name)
    )
