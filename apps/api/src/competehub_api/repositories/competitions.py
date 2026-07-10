from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from competehub_api.extensions import db
from competehub_api.models import Competition, CompetitionTag, CompetitionTagLink
from competehub_api.models.enums import CompetitionStatus

PUBLIC_COMPETITION_STATUSES = frozenset({CompetitionStatus.PUBLISHED})


def get_competition(competition_id: int) -> Competition | None:
    return db.session.get(Competition, competition_id)


def get_competition_tag_by_code(code: str) -> CompetitionTag | None:
    return db.session.scalar(select(CompetitionTag).where(CompetitionTag.code == code))


def public_competitions_statement():
    return select(Competition).where(Competition.status.in_(PUBLIC_COMPETITION_STATUSES))


def list_public_competitions() -> list[Competition]:
    statement = public_competitions_statement().options(
        selectinload(Competition.time_nodes),
        selectinload(Competition.tag_links).selectinload(CompetitionTagLink.tag),
    )
    return list(db.session.scalars(statement).unique())


def get_public_competition(competition_id: int) -> Competition | None:
    statement = (
        public_competitions_statement()
        .where(Competition.id == competition_id)
        .options(
            selectinload(Competition.time_nodes),
            selectinload(Competition.tag_links).selectinload(CompetitionTagLink.tag),
        )
    )
    return db.session.scalar(statement)
