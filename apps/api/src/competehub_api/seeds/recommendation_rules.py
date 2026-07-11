from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from competehub_api.extensions import db
from competehub_api.models import RecommendationRule, RecommendationRuleSet
from competehub_api.models.enums import RecommendationRuleSetStatus
from competehub_api.models.mixins import utc_now

CONTROLLED_RECOMMENDATION_RULE_CODES = (
    "major_match",
    "grade_match",
    "interest_match",
    "deadline_urgency",
    "general_fallback",
)


@dataclass(frozen=True)
class SeedRule:
    code: str
    name: str
    weight: int
    conditions: dict
    reason_template: str
    enabled: bool = True


INITIAL_RECOMMENDATION_RULES = (
    SeedRule(
        "major_match",
        "专业匹配",
        30,
        {"operator": "overlap"},
        "与你的专业 {major} 匹配",
    ),
    SeedRule(
        "grade_match",
        "年级匹配",
        20,
        {"operator": "overlap"},
        "适合你的年级 {grade}",
    ),
    SeedRule(
        "interest_match",
        "兴趣匹配",
        40,
        {"operator": "overlap"},
        "符合你的兴趣 {interest_tag}",
    ),
    SeedRule(
        "deadline_urgency",
        "截止时间临近",
        25,
        {"operator": "within_days", "min_days": 0, "max_days": 30},
        "报名截止日期为 {deadline_date}，还有 {days_remaining} 天",
    ),
    SeedRule(
        "general_fallback",
        "通用推荐",
        10,
        {"operator": "always"},
        "近期可行动的公开赛事",
    ),
)


class InitialRecommendationRuleSetConflict(RuntimeError):
    """The persisted v1 snapshot differs from the reproducible seed contract."""


def seed_initial_recommendation_rule_set() -> RecommendationRuleSet:
    existing = RecommendationRuleSet.query.filter_by(version=1).one_or_none()
    if existing is not None:
        _assert_matches_initial_seed(existing)
        return existing

    rule_set = RecommendationRuleSet(
        version=1,
        status=RecommendationRuleSetStatus.ACTIVE,
        activated_at=utc_now(),
        rules=[
            RecommendationRule(
                code=rule.code,
                name=rule.name,
                weight=rule.weight,
                conditions=rule.conditions,
                reason_template=rule.reason_template,
                enabled=rule.enabled,
            )
            for rule in INITIAL_RECOMMENDATION_RULES
        ],
    )
    db.session.add(rule_set)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        concurrent = RecommendationRuleSet.query.filter_by(version=1).one_or_none()
        if concurrent is None:
            raise
        _assert_matches_initial_seed(concurrent)
        return concurrent
    return rule_set


def _assert_matches_initial_seed(rule_set: RecommendationRuleSet) -> None:
    persisted = {
        rule.code: (
            rule.name,
            rule.weight,
            rule.conditions,
            rule.reason_template,
            rule.enabled,
        )
        for rule in rule_set.rules
    }
    expected = {
        rule.code: (
            rule.name,
            rule.weight,
            rule.conditions,
            rule.reason_template,
            rule.enabled,
        )
        for rule in INITIAL_RECOMMENDATION_RULES
    }
    if (
        rule_set.status != RecommendationRuleSetStatus.ACTIVE
        or rule_set.base_rule_set_id is not None
        or rule_set.cloned_from_rule_set_id is not None
        or persisted != expected
    ):
        raise InitialRecommendationRuleSetConflict(
            "recommendation rule-set v1 conflicts with the reproducible seed"
        )
