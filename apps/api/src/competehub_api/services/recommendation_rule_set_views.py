from __future__ import annotations

from competehub_api.models import RecommendationRuleSet, ReviewRecord, User
from competehub_api.models.enums import RecommendationRuleSetStatus
from competehub_api.repositories.recommendation_rule_sets import (
    list_recommendation_rule_sets,
    recommendation_rule_set_reviews,
    recommendation_rule_sets_by_ids,
    users_by_ids,
)
from competehub_api.schemas.recommendation_rule_sets import recommendation_rule_set_read_schema
from competehub_api.services.recommendation_rule_sets import (
    build_difference_snapshot,
    build_impact_summary,
)


def recommendation_rule_set_history() -> dict:
    return {"items": recommendation_rule_set_read_models(list_recommendation_rule_sets())}


def recommendation_rule_set_read_model(rule_set: RecommendationRuleSet) -> dict:
    return recommendation_rule_set_read_models([rule_set])[0]


def recommendation_rule_set_read_models(rule_sets: list[RecommendationRuleSet]) -> list[dict]:
    if not rule_sets:
        return []
    related_ids = {
        related_id
        for rule_set in rule_sets
        for related_id in (rule_set.cloned_from_rule_set_id, rule_set.base_rule_set_id)
        if related_id is not None
    }
    by_id = recommendation_rule_sets_by_ids({item.id for item in rule_sets} | related_ids)
    active = next(
        (item for item in by_id.values() if item.status == RecommendationRuleSetStatus.ACTIVE),
        None,
    )
    if active is None:
        active = next(
            (
                item
                for item in list_recommendation_rule_sets()
                if item.status == RecommendationRuleSetStatus.ACTIVE
            ),
            None,
        )
        if active is not None:
            by_id[active.id] = active
    reviews = recommendation_rule_set_reviews({item.id: item.version for item in rule_sets})
    user_ids = {
        user_id
        for rule_set in rule_sets
        for user_id in (
            rule_set.created_by_id,
            rule_set.submitted_by_id,
            rule_set.reviewed_by_id,
        )
        if user_id is not None
    }
    for review in reviews.values():
        user_ids.update(
            user_id
            for user_id in (review.submitted_by_id, review.reviewed_by_id)
            if user_id is not None
        )
    users = users_by_ids(user_ids)
    return [
        recommendation_rule_set_read_schema.dump(
            _build_read_model(rule_set, by_id, active, reviews.get(rule_set.id), users)
        )
        for rule_set in rule_sets
    ]


def _build_read_model(
    rule_set: RecommendationRuleSet,
    by_id: dict[int, RecommendationRuleSet],
    active: RecommendationRuleSet | None,
    decision: ReviewRecord | None,
    users: dict[int, User],
) -> dict:
    source = by_id.get(rule_set.cloned_from_rule_set_id)
    base = by_id.get(rule_set.base_rule_set_id)
    difference = None
    impact = None
    if decision is not None:
        difference = decision.difference_snapshot
        impact = decision.impact_summary
    elif base is not None and rule_set.status == RecommendationRuleSetStatus.PENDING_REVIEW:
        difference = build_difference_snapshot(base, rule_set)
        impact = build_impact_summary(base, rule_set, active)
    submitted_by_id = decision.submitted_by_id if decision is not None else rule_set.submitted_by_id
    reviewed_by_id = decision.reviewed_by_id if decision is not None else rule_set.reviewed_by_id
    return {
        "rule_set_id": rule_set.id,
        "version": rule_set.version,
        "status": rule_set.status.value,
        "created_by": _actor(users.get(rule_set.created_by_id)),
        "submitted_by": _actor(users.get(submitted_by_id)),
        "reviewed_by": _actor(users.get(reviewed_by_id)),
        "created_at": rule_set.created_at,
        "submitted_at": decision.submitted_at if decision is not None else rule_set.submitted_at,
        "decided_at": decision.decided_at if decision is not None else rule_set.decided_at,
        "activated_at": rule_set.activated_at,
        "retired_at": rule_set.retired_at,
        "review_comment": decision.comment if decision is not None else rule_set.review_comment,
        "terminal_review_status": decision.status.value if decision is not None else None,
        "cloned_from_rule_set_id": rule_set.cloned_from_rule_set_id,
        "cloned_from_version": source.version if source is not None else None,
        "base_rule_set_id": rule_set.base_rule_set_id,
        "base_version": base.version if base is not None else None,
        "active_rule_set_id": active.id if active is not None else None,
        "active_version": active.version if active is not None else None,
        "is_stale": _is_stale(rule_set, base, active),
        "difference_snapshot": difference,
        "impact_summary": impact,
        "rules": [
            {
                "code": rule.code,
                "name": rule.name,
                "weight": rule.weight,
                "conditions": rule.conditions,
                "reason_template": rule.reason_template,
                "enabled": rule.enabled,
            }
            for rule in rule_set.rules
        ],
    }


def _actor(user: User | None) -> dict | None:
    if user is None:
        return None
    return {"id": user.id, "display_name": user.display_name}


def _is_stale(
    rule_set: RecommendationRuleSet,
    base: RecommendationRuleSet | None,
    active: RecommendationRuleSet | None,
) -> bool:
    if rule_set.status == RecommendationRuleSetStatus.ACTIVE:
        return False
    return base is not None and (active is None or base.id != active.id)
