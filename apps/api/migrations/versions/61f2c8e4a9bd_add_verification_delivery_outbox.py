"""add verification delivery outbox

Revision ID: 61f2c8e4a9bd
Revises: c5e0e7e0560d
Create Date: 2026-07-12 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "61f2c8e4a9bd"
down_revision = "c5e0e7e0560d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "verification_delivery_outbox",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "challenge_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("delivery_nonce", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["identity_verification_challenges.id"],
            name=op.f(
                "fk_verification_delivery_outbox_challenge_id_identity_verification_challenges"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_delivery_outbox")),
        sa.UniqueConstraint(
            "challenge_id",
            name=op.f("uq_verification_delivery_outbox_challenge_id"),
        ),
    )
    op.create_index(
        "ix_verification_delivery_outbox_pending",
        "verification_delivery_outbox",
        ["delivered_at", "discarded_at", "available_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_verification_delivery_outbox_pending",
        table_name="verification_delivery_outbox",
    )
    op.drop_table("verification_delivery_outbox")
