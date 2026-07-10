from __future__ import annotations

from sqlalchemy import select

from competehub_api.extensions import db
from competehub_api.models import Competition, CompetitionTag
from competehub_api.models.enums import CompetitionStatus

PUBLIC_COMPETITION_STATUSES = frozenset({CompetitionStatus.PUBLISHED})


def get_competition(competition_id: int) -> Competition | None:
    return db.session.get(Competition, competition_id)


def get_competition_tag_by_code(code: str) -> CompetitionTag | None:
    return db.session.scalar(select(CompetitionTag).where(CompetitionTag.code == code))


def public_competitions_statement():
    return select(Competition).where(Competition.status.in_(PUBLIC_COMPETITION_STATUSES))
