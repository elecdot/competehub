from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from competehub_api.models import Competition, CompetitionTimeNode
from competehub_api.repositories.competitions import (
    PublicCompetitionPage,
    PublicCompetitionQuery,
    list_public_competition_candidates,
)

REGISTRATION_NODE_TYPES = frozenset({"registration_start", "registration_deadline"})
REGISTRATION_STATUS_ORDER = {
    "open": 0,
    "upcoming": 1,
    "unknown": 2,
    "not_applicable": 3,
    "closed": 4,
}


@dataclass(frozen=True)
class RegistrationStatus:
    value: str
    basis: CompetitionTimeNode | None = None


def search_public_competitions(query: PublicCompetitionQuery) -> PublicCompetitionPage:
    now = datetime.now(UTC)
    annotated = [
        (competition, registration_status(competition, now))
        for competition in list_public_competition_candidates(query)
    ]
    if query.registration_status is not None:
        annotated = [item for item in annotated if item[1].value == query.registration_status]
    annotated.sort(key=lambda item: _public_competition_order(item[0], item[1], query.sort, now))
    total = len(annotated)
    start = (query.page - 1) * query.page_size
    return PublicCompetitionPage(
        items=[competition for competition, _status in annotated[start : start + query.page_size]],
        page=query.page,
        page_size=query.page_size,
        total=total,
    )


def sorted_time_nodes(competition: Competition) -> list[CompetitionTimeNode]:
    return sorted(_published_time_nodes(competition), key=_time_node_sort_key)


def next_time_node(
    competition: Competition,
    at: datetime | None = None,
) -> CompetitionTimeNode | None:
    at = _as_utc(at or datetime.now(UTC))
    candidates = [
        (0 if node.prominence == "primary" else 1, node_time, node.id or 0, node)
        for node in _published_time_nodes(competition)
        if (node_time := _next_node_time(node, at)) is not None
    ]
    return min(candidates, default=(2, None, 0, None))[3]


def competition_tag_names(competition: Competition) -> list[str]:
    revision = competition.published_revision
    if revision is None:
        return []
    return sorted({link.tag.name for link in revision.tag_links if link.tag is not None})


def registration_status(
    competition: Competition,
    at: datetime | None = None,
) -> RegistrationStatus:
    revision = competition.published_revision
    if revision is None:
        return RegistrationStatus("unknown")
    if revision.registration_applicability == "not_applicable":
        return RegistrationStatus("not_applicable")

    at = _as_utc(at or datetime.now(UTC))
    stage_statuses = [
        _registration_stage_status(nodes, at) for nodes in _registration_stages(competition)
    ]
    for value in ("open", "upcoming", "closed"):
        matches = [status for status in stage_statuses if status.value == value]
        if matches:
            return min(matches, key=lambda status: _basis_time(status.basis))
    return RegistrationStatus("unknown")


def registration_status_sort_rank(value: str) -> int:
    return REGISTRATION_STATUS_ORDER[value]


def registration_status_time(status: RegistrationStatus) -> datetime | None:
    return _first_node_time(status.basis) if status.basis is not None else None


def _public_competition_order(
    competition: Competition,
    status: RegistrationStatus,
    sort: str,
    now: datetime,
) -> tuple:
    published_at = (
        competition.published_revision.published_at if competition.published_revision else None
    )
    published_at_key = -_as_utc_timestamp(published_at)
    if sort == "published_at":
        return (published_at_key, -(competition.id or 0))

    registration_deadline = _future_registration_deadline(competition, now)
    if sort == "registration_deadline":
        return (
            _missing_time_last(registration_deadline),
            registration_deadline or datetime.max.replace(tzinfo=UTC),
            published_at_key,
            -(competition.id or 0),
        )

    relevant_time = registration_status_time(status)
    if status.value not in {"open", "upcoming"}:
        node = next_time_node(competition, now)
        relevant_time = node.occurs_at if node is not None else None
    return (
        registration_status_sort_rank(status.value),
        _missing_time_last(relevant_time),
        relevant_time or datetime.max.replace(tzinfo=UTC),
        published_at_key,
        -(competition.id or 0),
    )


def _future_registration_deadline(
    competition: Competition,
    now: datetime,
) -> datetime | None:
    deadlines = (
        [
            node.occurs_at
            for node in competition.published_revision.time_nodes
            if node.node_type == "registration_deadline"
            and node.occurs_at is not None
            and _as_utc(node.occurs_at) >= now
        ]
        if competition.published_revision
        else []
    )
    return min((_as_utc(value) for value in deadlines), default=None)


def _missing_time_last(value: datetime | None) -> int:
    return 1 if value is None else 0


def _as_utc_timestamp(value: datetime | None) -> float:
    if value is None:
        return float("-inf")
    return _as_utc(value).timestamp()


def _published_time_nodes(competition: Competition) -> list[CompetitionTimeNode]:
    revision = competition.published_revision
    return revision.time_nodes if revision is not None else []


def _registration_stages(competition: Competition) -> list[list[CompetitionTimeNode]]:
    grouped: dict[int | None, list[CompetitionTimeNode]] = {}
    for node in _published_time_nodes(competition):
        if node.node_type in REGISTRATION_NODE_TYPES:
            grouped.setdefault(node.stage_id, []).append(node)
    return list(grouped.values())


def _registration_stage_status(
    nodes: list[CompetitionTimeNode],
    at: datetime,
) -> RegistrationStatus:
    future_starts = [
        node for node in nodes if node.node_type == "registration_start" and _is_future(node, at)
    ]
    future_deadlines = [
        node for node in nodes if node.node_type == "registration_deadline" and _is_future(node, at)
    ]
    if future_starts:
        return RegistrationStatus("upcoming", min(future_starts, key=_node_time_sort_key))
    if future_deadlines:
        return RegistrationStatus("open", min(future_deadlines, key=_node_time_sort_key))

    deadlines = [node for node in nodes if node.node_type == "registration_deadline"]
    is_closed = deadlines and all(
        _first_node_time(node) is not None and _first_node_time(node) < at for node in deadlines
    )
    if is_closed:
        return RegistrationStatus("closed", max(deadlines, key=_node_time_sort_key))
    return RegistrationStatus("unknown")


def _time_node_sort_key(node: CompetitionTimeNode) -> tuple[datetime, int]:
    return (_first_node_time(node) or datetime.max.replace(tzinfo=UTC), node.id or 0)


def _node_time_sort_key(node: CompetitionTimeNode) -> tuple[datetime, int]:
    return _time_node_sort_key(node)


def _basis_time(node: CompetitionTimeNode | None) -> tuple[datetime, int]:
    if node is None:
        return (datetime.max.replace(tzinfo=UTC), 0)
    return _node_time_sort_key(node)


def _node_times(node: CompetitionTimeNode) -> list[datetime]:
    return sorted(
        _as_utc(value)
        for value in (node.occurs_at, node.starts_at, node.due_at)
        if value is not None
    )


def _first_node_time(node: CompetitionTimeNode) -> datetime | None:
    return next(iter(_node_times(node)), None)


def _next_node_time(node: CompetitionTimeNode, at: datetime) -> datetime | None:
    return next((value for value in _node_times(node) if value >= at), None)


def _is_future(node: CompetitionTimeNode, at: datetime) -> bool:
    value = _first_node_time(node)
    return value is not None and value >= at


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
