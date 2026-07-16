from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from competehub_api.extensions import db
from competehub_api.models import RecommendationRuleSet, ReviewRecord, User
from competehub_api.models.enums import RecommendationRuleSetStatus


def get_active_recommendation_rule_set() -> RecommendationRuleSet | None:
    statement = (
        select(RecommendationRuleSet)
        .where(RecommendationRuleSet.status == RecommendationRuleSetStatus.ACTIVE)
        .options(selectinload(RecommendationRuleSet.rules))
    )
    return db.session.scalars(statement).unique().one_or_none()


def list_recommendation_rule_sets() -> list[RecommendationRuleSet]:
    statement = (
        select(RecommendationRuleSet)
        .options(selectinload(RecommendationRuleSet.rules))
        .order_by(RecommendationRuleSet.version.desc())
    )
    return list(db.session.scalars(statement).unique())


def recommendation_rule_sets_by_ids(rule_set_ids: set[int]) -> dict[int, RecommendationRuleSet]:
    if not rule_set_ids:
        return {}
    statement = (
        select(RecommendationRuleSet)
        .where(RecommendationRuleSet.id.in_(rule_set_ids))
        .options(selectinload(RecommendationRuleSet.rules))
    )
    return {item.id: item for item in db.session.scalars(statement).unique()}


def recommendation_rule_set_reviews(
    rule_set_versions: dict[int, int],
) -> dict[int, ReviewRecord]:
    if not rule_set_versions:
        return {}
    statement = select(ReviewRecord).where(
        ReviewRecord.target_type == "recommendation_rule_set",
        ReviewRecord.target_id.in_(rule_set_versions),
    )
    return {
        review.target_id: review
        for review in db.session.scalars(statement)
        if review.target_revision == rule_set_versions[review.target_id]
    }


def users_by_ids(user_ids: set[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    return {user.id: user for user in db.session.scalars(select(User).where(User.id.in_(user_ids)))}
