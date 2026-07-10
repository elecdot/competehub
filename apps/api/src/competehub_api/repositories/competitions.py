from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, case, cast, exists, false, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionTag,
    CompetitionTagLink,
    CompetitionTimeNode,
)
from competehub_api.models.enums import CompetitionStatus

PUBLIC_COMPETITION_STATUSES = frozenset({CompetitionStatus.PUBLISHED})


@dataclass(frozen=True)
class PublicCompetitionQuery:
    page: int = 1
    page_size: int = 20
    keyword: str | None = None
    category: str | None = None
    major: str | None = None
    grade: str | None = None
    tag: str | None = None
    status: str | None = None
    participant_form: str | None = None
    deadline_from: date | None = None
    deadline_to: date | None = None


@dataclass(frozen=True)
class PublicCompetitionPage:
    items: list[Competition]
    page: int
    page_size: int
    total: int


def get_competition(competition_id: int) -> Competition | None:
    return db.session.get(Competition, competition_id)


def get_competition_tag_by_code(code: str) -> CompetitionTag | None:
    return db.session.scalar(select(CompetitionTag).where(CompetitionTag.code == code))


def public_competitions_statement():
    return select(Competition).where(Competition.status.in_(PUBLIC_COMPETITION_STATUSES))


def search_public_competitions(query: PublicCompetitionQuery) -> PublicCompetitionPage:
    conditions = _public_competition_conditions(query)
    total = db.session.scalar(select(func.count(Competition.id)).where(*conditions)) or 0
    now = datetime.now(UTC)
    statement = (
        select(Competition)
        .where(*conditions)
        .order_by(*_public_competition_order(now))
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
        .options(*_public_relation_options())
    )
    return PublicCompetitionPage(
        items=list(db.session.scalars(statement).unique()),
        page=query.page,
        page_size=query.page_size,
        total=total,
    )


def get_public_competition(competition_id: int) -> Competition | None:
    statement = (
        public_competitions_statement()
        .where(Competition.id == competition_id)
        .options(*_public_relation_options())
    )
    return db.session.scalar(statement)


def _public_relation_options():
    return (
        selectinload(Competition.time_nodes),
        selectinload(Competition.tag_links).selectinload(CompetitionTagLink.tag),
    )


def _public_competition_conditions(query: PublicCompetitionQuery) -> list:
    conditions = [Competition.status.in_(PUBLIC_COMPETITION_STATUSES)]
    if query.status is not None and query.status != CompetitionStatus.PUBLISHED.value:
        conditions.append(false())
    if query.keyword is not None:
        pattern = f"%{_escape_like(query.keyword)}%"
        conditions.append(
            or_(
                Competition.title.ilike(pattern, escape="\\"),
                Competition.short_title.ilike(pattern, escape="\\"),
                Competition.organizer.ilike(pattern, escape="\\"),
                Competition.category.ilike(pattern, escape="\\"),
                Competition.summary.ilike(pattern, escape="\\"),
            )
        )
    if query.category is not None:
        conditions.append(Competition.category == query.category)
    if query.participant_form is not None:
        conditions.append(Competition.participant_form == query.participant_form)
    if query.major is not None:
        conditions.append(_json_array_contains(Competition.suitable_majors, query.major))
    if query.grade is not None:
        conditions.append(_json_array_contains(Competition.suitable_grades, query.grade))
    if query.tag is not None:
        conditions.append(
            Competition.tag_links.any(CompetitionTagLink.tag.has(CompetitionTag.name == query.tag))
        )
    deadline_condition = _deadline_condition(query)
    if deadline_condition is not None:
        conditions.append(Competition.time_nodes.any(deadline_condition))
    return conditions


def _json_array_contains(column, value: str):
    if db.session.get_bind().dialect.name == "postgresql":
        return cast(column, JSONB).contains([value])

    values = func.json_each(column).table_valued("key", "value").alias()
    return exists(select(1).select_from(values).where(values.c.value == value))


def _deadline_condition(query: PublicCompetitionQuery):
    conditions = []
    if query.deadline_from is not None:
        conditions.append(
            CompetitionTimeNode.due_at
            >= datetime.combine(query.deadline_from, time.min, tzinfo=UTC)
        )
    if query.deadline_to is not None:
        exclusive_end = query.deadline_to + timedelta(days=1)
        conditions.append(
            CompetitionTimeNode.due_at < datetime.combine(exclusive_end, time.min, tzinfo=UTC)
        )
    return and_(*conditions) if conditions else None


def _public_competition_order(now: datetime) -> tuple:
    next_start = (
        select(func.min(CompetitionTimeNode.starts_at))
        .where(
            CompetitionTimeNode.competition_id == Competition.id,
            CompetitionTimeNode.starts_at >= now,
        )
        .correlate(Competition)
        .scalar_subquery()
    )
    next_due = (
        select(func.min(CompetitionTimeNode.due_at))
        .where(
            CompetitionTimeNode.competition_id == Competition.id,
            CompetitionTimeNode.due_at >= now,
        )
        .correlate(Competition)
        .scalar_subquery()
    )
    next_at = case(
        (next_start.is_(None), next_due),
        (next_due.is_(None), next_start),
        (next_start <= next_due, next_start),
        else_=next_due,
    )
    return (
        case((next_at.is_(None), 1), else_=0),
        next_at,
        Competition.title,
        Competition.id,
    )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
