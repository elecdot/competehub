from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from competehub_api.models import Competition, CompetitionTimeNode
from competehub_api.models.enums import CompetitionStatus
from competehub_api.repositories.competitions import list_public_competitions


@dataclass(frozen=True)
class CompetitionSearchCriteria:
    page: int = 1
    page_size: int = 20
    keyword: str | None = None
    category: str | None = None
    major: str | None = None
    grade: str | None = None
    tag: str | None = None
    status: str | None = None
    participant_form: str | None = None


@dataclass(frozen=True)
class PublicCompetitionPage:
    items: list[Competition]
    page: int
    page_size: int
    total: int


def search_public_competitions(
    criteria: CompetitionSearchCriteria,
) -> PublicCompetitionPage:
    competitions = [
        competition
        for competition in list_public_competitions()
        if _matches_filters(competition, criteria)
    ]
    now = datetime.now(UTC)
    competitions.sort(key=lambda competition: _competition_sort_key(competition, now))

    start = (criteria.page - 1) * criteria.page_size
    end = start + criteria.page_size
    return PublicCompetitionPage(
        items=competitions[start:end],
        page=criteria.page,
        page_size=criteria.page_size,
        total=len(competitions),
    )


def sorted_time_nodes(competition: Competition) -> list[CompetitionTimeNode]:
    return sorted(competition.time_nodes, key=_time_node_sort_key)


def next_time_node(
    competition: Competition,
    at: datetime | None = None,
) -> CompetitionTimeNode | None:
    at = _as_utc(at or datetime.now(UTC))
    for node in sorted_time_nodes(competition):
        node_time = _node_time(node)
        if node_time is not None and node_time >= at:
            return node
    return None


def competition_tag_names(competition: Competition) -> list[str]:
    return sorted({link.tag.name for link in competition.tag_links if link.tag is not None})


def _matches_filters(
    competition: Competition,
    criteria: CompetitionSearchCriteria,
) -> bool:
    if criteria.status is not None and criteria.status != CompetitionStatus.PUBLISHED.value:
        return False

    if criteria.keyword is not None:
        haystack = " ".join(
            value or ""
            for value in (
                competition.title,
                competition.short_title,
                competition.organizer,
                competition.category,
                competition.summary,
            )
        ).lower()
        if criteria.keyword.lower() not in haystack:
            return False

    if criteria.category is not None and competition.category != criteria.category:
        return False
    if (
        criteria.participant_form is not None
        and competition.participant_form != criteria.participant_form
    ):
        return False
    if criteria.major is not None and criteria.major not in (competition.suitable_majors or []):
        return False
    if criteria.grade is not None and criteria.grade not in (competition.suitable_grades or []):
        return False
    return criteria.tag is None or criteria.tag in competition_tag_names(competition)


def _competition_sort_key(
    competition: Competition,
    now: datetime,
) -> tuple[datetime, str]:
    node = next_time_node(competition, now)
    return (_node_time(node) or datetime.max.replace(tzinfo=UTC), competition.title)


def _time_node_sort_key(node: CompetitionTimeNode) -> tuple[datetime, int]:
    return (_node_time(node) or datetime.max.replace(tzinfo=UTC), node.id or 0)


def _node_time(node: CompetitionTimeNode | None) -> datetime | None:
    if node is None:
        return None
    value = node.due_at or node.starts_at
    return _as_utc(value) if value is not None else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
