from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, cast, exists, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    CompetitionStage,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
)
from competehub_api.models.enums import CompetitionRevisionStatus, CompetitionStatus
from competehub_api.services.competition_discovery import (
    next_time_node,
    registration_status,
    registration_status_sort_rank,
    registration_status_time,
)
from competehub_api.timezones import product_date_start_utc

PUBLIC_COMPETITION_STATUSES = frozenset({CompetitionStatus.PUBLISHED})
PUBLIC_DETAIL_STATUSES = frozenset(
    {
        CompetitionStatus.PUBLISHED,
        CompetitionStatus.CANCELLED,
        CompetitionStatus.ARCHIVED,
        CompetitionStatus.EXPIRED,
    }
)


@dataclass(frozen=True)
class PublicCompetitionQuery:
    page: int = 1
    page_size: int = 20
    keyword: str | None = None
    category: str | None = None
    major: str | None = None
    grade: str | None = None
    tag: str | None = None
    registration_status: str | None = None
    participant_form: str | None = None
    deadline_from: date | None = None
    deadline_to: date | None = None
    sort: str = "actionable"


@dataclass(frozen=True)
class PublicCompetitionPage:
    items: list[Competition]
    page: int
    page_size: int
    total: int


def get_competition(competition_id: int) -> Competition | None:
    return db.session.get(Competition, competition_id)


def get_competition_by_series_edition(series_id: int, edition_label: str) -> Competition | None:
    return db.session.scalar(
        select(Competition).where(
            Competition.series_id == series_id,
            Competition.edition_label == edition_label,
        )
    )


def get_edition_workspace(competition_id: int) -> Competition | None:
    statement = (
        select(Competition)
        .where(Competition.id == competition_id)
        .options(
            selectinload(Competition.revisions)
            .selectinload(CompetitionRevision.stages)
            .selectinload(CompetitionStage.time_nodes),
            selectinload(Competition.revisions)
            .selectinload(CompetitionRevision.tag_links)
            .selectinload(CompetitionTagLink.tag),
            selectinload(Competition.published_revision),
        )
    )
    return db.session.scalar(statement)


def list_edition_workspaces() -> list[Competition]:
    statement = (
        select(Competition)
        .where(Competition.series_id.is_not(None))
        .options(
            selectinload(Competition.series),
            selectinload(Competition.revisions)
            .selectinload(CompetitionRevision.stages)
            .selectinload(CompetitionStage.time_nodes),
            selectinload(Competition.revisions)
            .selectinload(CompetitionRevision.tag_links)
            .selectinload(CompetitionTagLink.tag),
            selectinload(Competition.published_revision),
        )
        .order_by(Competition.edition_label.desc(), Competition.id.desc())
    )
    return list(db.session.scalars(statement).unique())


def get_competition_series(series_id: int) -> CompetitionSeries | None:
    return db.session.get(CompetitionSeries, series_id)


def get_competition_series_by_name(name: str) -> CompetitionSeries | None:
    return db.session.scalar(
        select(CompetitionSeries).where(CompetitionSeries.canonical_name == name)
    )


def list_competition_series() -> list[CompetitionSeries]:
    return list(
        db.session.scalars(select(CompetitionSeries).order_by(CompetitionSeries.canonical_name))
    )


def get_competition_revision(revision_id: int) -> CompetitionRevision | None:
    statement = (
        select(CompetitionRevision)
        .where(CompetitionRevision.id == revision_id)
        .options(
            selectinload(CompetitionRevision.stages).selectinload(CompetitionStage.time_nodes),
            selectinload(CompetitionRevision.tag_links).selectinload(CompetitionTagLink.tag),
            selectinload(CompetitionRevision.competition),
        )
    )
    return db.session.scalar(statement)


def get_competition_for_update(competition_id: int) -> Competition | None:
    return db.session.scalar(
        select(Competition)
        .where(Competition.id == competition_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def get_competition_revision_for_update(revision_id: int) -> CompetitionRevision | None:
    return db.session.scalar(
        select(CompetitionRevision)
        .where(CompetitionRevision.id == revision_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def get_active_competition_revision(competition_id: int) -> CompetitionRevision | None:
    return db.session.scalar(
        select(CompetitionRevision).where(
            CompetitionRevision.competition_id == competition_id,
            CompetitionRevision.revision_status.in_(
                [CompetitionRevisionStatus.DRAFT, CompetitionRevisionStatus.PENDING_REVIEW]
            ),
        )
    )


def get_latest_terminal_competition_revision(
    competition_id: int,
) -> CompetitionRevision | None:
    return db.session.scalar(
        select(CompetitionRevision)
        .where(
            CompetitionRevision.competition_id == competition_id,
            CompetitionRevision.revision_status.in_(
                [CompetitionRevisionStatus.REJECTED, CompetitionRevisionStatus.RETURNED]
            ),
        )
        .order_by(CompetitionRevision.revision_number.desc())
        .limit(1)
    )


def list_competition_revisions(status: str | None = None) -> list[CompetitionRevision]:
    statement = select(CompetitionRevision).options(
        selectinload(CompetitionRevision.stages).selectinload(CompetitionStage.time_nodes),
        selectinload(CompetitionRevision.tag_links).selectinload(CompetitionTagLink.tag),
        selectinload(CompetitionRevision.competition),
    )
    if status is not None:
        statement = statement.where(CompetitionRevision.revision_status == status)
    return list(
        db.session.scalars(
            statement.order_by(CompetitionRevision.submitted_at, CompetitionRevision.id)
        ).unique()
    )


def get_competition_tag_by_code(code: str) -> CompetitionTag | None:
    return db.session.scalar(select(CompetitionTag).where(CompetitionTag.code == code))


def public_competitions_statement():
    return select(Competition).where(
        Competition.status.in_(PUBLIC_COMPETITION_STATUSES),
        Competition.published_revision_id.is_not(None),
    )


def search_public_competitions(query: PublicCompetitionQuery) -> PublicCompetitionPage:
    conditions = _public_competition_conditions(query)
    now = datetime.now(UTC)
    statement = select(Competition).where(*conditions).options(*_public_relation_options())
    competitions = list(db.session.scalars(statement).unique())
    annotated = [
        (competition, registration_status(competition, now)) for competition in competitions
    ]
    if query.registration_status is not None:
        annotated = [item for item in annotated if item[1].value == query.registration_status]
    annotated.sort(key=lambda item: _public_competition_order(item[0], item[1], query.sort, now))
    total = len(annotated)
    start = (query.page - 1) * query.page_size
    page_items = [
        competition for competition, _status in annotated[start : start + query.page_size]
    ]
    return PublicCompetitionPage(
        items=page_items,
        page=query.page,
        page_size=query.page_size,
        total=total,
    )


def get_public_competition(competition_id: int) -> Competition | None:
    statement = (
        select(Competition)
        .where(
            Competition.id == competition_id,
            Competition.status.in_(PUBLIC_DETAIL_STATUSES),
            Competition.published_revision_id.is_not(None),
        )
        .options(*_public_relation_options())
    )
    return db.session.scalar(statement)


def list_competitions_with_current_published_revision(
    competition_ids: list[int],
) -> list[Competition]:
    """Load preview fixtures and exactly the revision selected by each public pointer."""
    if not competition_ids:
        return []
    statement = (
        select(Competition)
        .where(Competition.id.in_(competition_ids))
        .options(*_public_relation_options())
        .order_by(Competition.id)
    )
    return list(db.session.scalars(statement).unique())


def _public_relation_options():
    return (
        selectinload(Competition.published_revision)
        .selectinload(CompetitionRevision.time_nodes)
        .selectinload(CompetitionTimeNode.stage),
        selectinload(Competition.published_revision)
        .selectinload(CompetitionRevision.tag_links)
        .selectinload(CompetitionTagLink.tag),
    )


def _public_competition_conditions(query: PublicCompetitionQuery) -> list:
    conditions = [
        Competition.status.in_(PUBLIC_COMPETITION_STATUSES),
        Competition.published_revision_id.is_not(None),
    ]
    if query.keyword is not None:
        pattern = f"%{_escape_like(query.keyword)}%"
        conditions.append(
            Competition.published_revision.has(
                or_(
                    CompetitionRevision.title.ilike(pattern, escape="\\"),
                    CompetitionRevision.short_title.ilike(pattern, escape="\\"),
                    CompetitionRevision.organizer.ilike(pattern, escape="\\"),
                    CompetitionRevision.category.ilike(pattern, escape="\\"),
                    CompetitionRevision.summary.ilike(pattern, escape="\\"),
                )
            )
        )
    if query.category is not None:
        conditions.append(
            Competition.published_revision.has(CompetitionRevision.category == query.category)
        )
    if query.participant_form is not None:
        conditions.append(
            Competition.published_revision.has(
                _json_array_contains(CompetitionRevision.participant_forms, query.participant_form)
            )
        )
    if query.major is not None:
        conditions.append(
            Competition.published_revision.has(
                or_(
                    CompetitionRevision.major_scope == "all",
                    and_(
                        CompetitionRevision.major_scope == "selected",
                        _json_array_contains(CompetitionRevision.suitable_majors, query.major),
                    ),
                ),
            )
        )
    if query.grade is not None:
        conditions.append(
            Competition.published_revision.has(
                or_(
                    CompetitionRevision.grade_scope == "all",
                    and_(
                        CompetitionRevision.grade_scope == "selected",
                        _json_array_contains(CompetitionRevision.suitable_grades, query.grade),
                    ),
                ),
            )
        )
    if query.tag is not None:
        conditions.append(
            Competition.published_revision.has(
                CompetitionRevision.tag_links.any(
                    CompetitionTagLink.tag.has(CompetitionTag.name == query.tag)
                )
            )
        )
    deadline_condition = _deadline_condition(query)
    if deadline_condition is not None:
        conditions.append(
            Competition.published_revision.has(
                CompetitionRevision.time_nodes.any(deadline_condition)
            )
        )
    return conditions


def _json_array_contains(column, value: str):
    if db.session.get_bind().dialect.name == "postgresql":
        return cast(column, JSONB).contains([value])

    values = func.json_each(column).table_valued("key", "value").alias()
    return exists(select(1).select_from(values).where(values.c.value == value))


def _deadline_condition(query: PublicCompetitionQuery):
    if query.deadline_from is None and query.deadline_to is None:
        return None

    conditions = [CompetitionTimeNode.node_type == "registration_deadline"]
    if query.deadline_from is not None:
        conditions.append(
            CompetitionTimeNode.occurs_at >= product_date_start_utc(query.deadline_from)
        )
    if query.deadline_to is not None:
        exclusive_end = query.deadline_to + timedelta(days=1)
        conditions.append(CompetitionTimeNode.occurs_at < product_date_start_utc(exclusive_end))
    return and_(*conditions)


def _public_competition_order(competition, status, sort: str, now: datetime) -> tuple:
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


def _future_registration_deadline(competition: Competition, now: datetime) -> datetime | None:
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


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
