from __future__ import annotations

from collections.abc import Iterable

SUBSCRIPTION_NODE_TYPES = (
    "registration_deadline",
    "submission_deadline",
    "competition_start",
)


def canonical_subscription_node_types(node_types: Iterable[str]) -> list[str]:
    values = list(node_types)
    unknown = set(values) - set(SUBSCRIPTION_NODE_TYPES)
    if unknown:
        raise ValueError(f"Unknown subscription node types: {sorted(unknown)!r}")
    if len(values) != len(set(values)):
        raise ValueError("Subscription node types must not contain duplicates.")
    return [node_type for node_type in SUBSCRIPTION_NODE_TYPES if node_type in values]
