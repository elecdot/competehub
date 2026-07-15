"""canonicalize subscription node types

Revision ID: 4d8b6e1a3f20
Revises: 7f3c2a91d8e4
Create Date: 2026-07-14 12:00:00
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4d8b6e1a3f20"
down_revision = "7f3c2a91d8e4"
branch_labels = None
depends_on = None

SUBSCRIPTION_NODE_TYPES = (
    "registration_deadline",
    "submission_deadline",
    "competition_start",
)


def upgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()
    metadata.reflect(bind=bind, only=["subscriptions"])
    subscriptions = metadata.tables["subscriptions"]
    if "node_types" not in subscriptions.c:
        return
    invalid_row_ids = []
    updates = []
    for row in bind.execute(sa.select(subscriptions.c.id, subscriptions.c.node_types)).mappings():
        try:
            canonical = _canonical_node_types(row["node_types"])
        except ValueError:
            invalid_row_ids.append(row["id"])
            continue
        if canonical != _decoded_json(row["node_types"]):
            updates.append({"subscription_id": row["id"], "node_types": canonical})

    if invalid_row_ids:
        identifiers = ", ".join(str(row_id) for row_id in invalid_row_ids)
        raise RuntimeError(
            "Cannot canonicalize subscriptions.node_types; invalid subscription row IDs: "
            f"{identifiers}"
        )
    for update in updates:
        bind.execute(
            subscriptions.update()
            .where(subscriptions.c.id == update["subscription_id"])
            .values(node_types=update["node_types"])
        )


def downgrade():
    # Ordering normalization is lossless; prior request order was never contractual.
    pass


def _canonical_node_types(value) -> list[str]:
    values = _decoded_json(value)
    if not isinstance(values, list) or any(not isinstance(node_type, str) for node_type in values):
        raise ValueError("node_types must be a JSON list of strings")
    if len(values) != len(set(values)):
        raise ValueError("node_types must not contain duplicates")
    if set(values) - set(SUBSCRIPTION_NODE_TYPES):
        raise ValueError("node_types contains unknown values")
    return [node_type for node_type in SUBSCRIPTION_NODE_TYPES if node_type in values]


def _decoded_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("node_types is not valid JSON") from error
    return value
