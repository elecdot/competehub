from __future__ import annotations

from datetime import UTC, datetime

from competehub_api.models import Competition, CompetitionTimeNode


def sorted_time_nodes(competition: Competition) -> list[CompetitionTimeNode]:
    return sorted(competition.time_nodes, key=_time_node_sort_key)


def next_time_node(
    competition: Competition,
    at: datetime | None = None,
) -> CompetitionTimeNode | None:
    at = _as_utc(at or datetime.now(UTC))
    candidates = [
        (node_time, node.id or 0, node)
        for node in competition.time_nodes
        if (node_time := _next_node_time(node, at)) is not None
    ]
    return min(candidates, default=(None, 0, None))[2]


def competition_tag_names(competition: Competition) -> list[str]:
    return sorted({link.tag.name for link in competition.tag_links if link.tag is not None})


def _time_node_sort_key(node: CompetitionTimeNode) -> tuple[datetime, int]:
    return (_first_node_time(node) or datetime.max.replace(tzinfo=UTC), node.id or 0)


def _node_times(node: CompetitionTimeNode) -> list[datetime]:
    return sorted(_as_utc(value) for value in (node.starts_at, node.due_at) if value is not None)


def _first_node_time(node: CompetitionTimeNode) -> datetime | None:
    return next(iter(_node_times(node)), None)


def _next_node_time(node: CompetitionTimeNode, at: datetime) -> datetime | None:
    return next((value for value in _node_times(node) if value >= at), None)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
