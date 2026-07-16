from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from marshmallow import ValidationError

from competehub_api.models import Competition, RecommendationRuleSet, User
from competehub_api.models.enums import RecommendationRuleSetStatus, UserRole
from competehub_api.repositories.competitions import PublicCompetitionQuery
from competehub_api.repositories.recommendation_rule_sets import (
    get_active_recommendation_rule_set,
)
from competehub_api.schemas.recommendation_rule_sets import recommendation_rule_input_schema
from competehub_api.services.competition_discovery import list_ordered_public_competitions
from competehub_api.services.profiles import missing_fields, profile_status
from competehub_api.services.recommendation_engine import (
    PERSONALIZED_RULE_CODES,
    RankedRecommendation,
    RecommendationMode,
    rank_recommendation_candidates,
)

RECOMMENDATION_LIMIT = 20
NO_ACTIVE_RULE_SET_GENERAL_REASON = "按当前报名可行动性排序的公开赛事"


class GeneralFallbackCause(StrEnum):
    """Internal fallback causes; public reason-code mapping remains an API concern."""

    ANONYMOUS = "anonymous"
    PROFILE_INCOMPLETE = "profile_incomplete"
    NO_ACTIVE_RULE_SET = "no_active_rule_set"


@dataclass(frozen=True)
class RecommendationContext:
    mode: RecommendationMode
    profile_status: str | None
    missing_fields: tuple[str, ...]
    fallback_cause: GeneralFallbackCause | None
    rule_set_id: int | None
    rule_set_version: int | None


@dataclass(frozen=True)
class RecommendationFeed:
    context: RecommendationContext
    items: tuple[RankedRecommendation, ...]


def recommend_competitions(
    user: User | None,
    *,
    evaluation_time: datetime | None = None,
) -> RecommendationFeed:
    """Build one public feed from governed rules and published discovery candidates."""
    evaluation_time = evaluation_time or datetime.now(UTC)
    selected_rule_set = get_active_recommendation_rule_set()
    active_rule_set = selected_rule_set if _is_valid_active_rule_set(selected_rule_set) else None
    context = resolve_recommendation_context(user, active_rule_set)
    candidates = list_ordered_public_competitions(
        PublicCompetitionQuery(sort="actionable"),
        at=evaluation_time,
    )

    if context.mode == RecommendationMode.PERSONALIZED:
        ranked = rank_recommendation_candidates(
            candidates=candidates,
            rules=active_rule_set.rules,
            mode=context.mode,
            profile=_profile_facts(user),
            evaluation_time=evaluation_time,
            rule_set_version=active_rule_set.version,
        )
        matched_ids = {item.competition.id for item in ranked}
        supplemented = _general_recommendations(
            [candidate for candidate in candidates if candidate.id not in matched_ids],
            reason=_general_reason(active_rule_set),
            mode=RecommendationMode.PERSONALIZED,
            rule_set_version=active_rule_set.version,
        )
        items = _reposition([*ranked, *supplemented])
    else:
        reason = (
            _general_reason(active_rule_set)
            if active_rule_set is not None
            else NO_ACTIVE_RULE_SET_GENERAL_REASON
        )
        items = _general_recommendations(
            candidates,
            reason=reason,
            mode=RecommendationMode.GENERAL,
            rule_set_version=None,
        )
    return RecommendationFeed(context=context, items=tuple(items[:RECOMMENDATION_LIMIT]))


def resolve_recommendation_context(
    user: User | None,
    active_rule_set: RecommendationRuleSet | None,
) -> RecommendationContext:
    """Resolve mode and immutable rule-set identity without discovering candidates."""
    if user is None:
        return _general_context(GeneralFallbackCause.ANONYMOUS)

    if user.role is not None and user.role != UserRole.STUDENT:
        return _general_context(GeneralFallbackCause.ANONYMOUS)

    profile = user.profile
    if profile is None:
        return _general_context(
            GeneralFallbackCause.PROFILE_INCOMPLETE,
            profile_status_value="incomplete",
            missing=("college", "major", "grade", "interest_tags"),
        )

    missing = tuple(missing_fields(profile))
    status = profile_status(profile)
    if missing:
        return _general_context(
            GeneralFallbackCause.PROFILE_INCOMPLETE,
            profile_status_value=status,
            missing=missing,
        )
    if not _is_valid_active_rule_set(active_rule_set):
        return _general_context(
            GeneralFallbackCause.NO_ACTIVE_RULE_SET,
            profile_status_value=status,
        )
    return RecommendationContext(
        mode=RecommendationMode.PERSONALIZED,
        profile_status=status,
        missing_fields=(),
        fallback_cause=None,
        rule_set_id=active_rule_set.id,
        rule_set_version=active_rule_set.version,
    )


def _general_context(
    fallback_cause: GeneralFallbackCause,
    *,
    profile_status_value: str | None = None,
    missing: tuple[str, ...] = (),
) -> RecommendationContext:
    return RecommendationContext(
        mode=RecommendationMode.GENERAL,
        profile_status=profile_status_value,
        missing_fields=missing,
        fallback_cause=fallback_cause,
        rule_set_id=None,
        rule_set_version=None,
    )


def _profile_facts(user: User) -> dict:
    profile = user.profile
    return {
        "college": profile.college,
        "major": profile.major,
        "grade": profile.grade,
        "interest_tags": list(profile.interest_tags or []),
    }


def _is_valid_active_rule_set(rule_set: RecommendationRuleSet | None) -> bool:
    if rule_set is None or rule_set.status != RecommendationRuleSetStatus.ACTIVE:
        return False
    snapshots = [
        {
            "code": rule.code,
            "name": rule.name,
            "weight": rule.weight,
            "conditions": rule.conditions,
            "reason_template": rule.reason_template,
            "enabled": rule.enabled,
        }
        for rule in rule_set.rules
    ]
    try:
        recommendation_rule_input_schema.load(snapshots, many=True)
    except ValidationError:
        return False
    codes = [snapshot["code"] for snapshot in snapshots]
    if len(codes) != len(set(codes)):
        return False
    enabled_codes = {snapshot["code"] for snapshot in snapshots if snapshot["enabled"]}
    return "general_fallback" in enabled_codes and bool(enabled_codes & PERSONALIZED_RULE_CODES)


def _general_reason(rule_set: RecommendationRuleSet) -> str:
    fallback = next(
        (rule for rule in rule_set.rules if rule.enabled and rule.code == "general_fallback"),
        None,
    )
    if fallback is None:
        # Active rule sets are validated before activation. Treat a corrupted snapshot
        # like missing configuration instead of inventing personalized behavior.
        return NO_ACTIVE_RULE_SET_GENERAL_REASON
    return fallback.reason_template


def _general_recommendations(
    candidates: list[Competition],
    *,
    reason: str,
    mode: RecommendationMode,
    rule_set_version: int | None,
) -> list[RankedRecommendation]:
    return [
        RankedRecommendation(
            position=position,
            competition=competition,
            reason_codes=("general_fallback",),
            reasons=(reason,),
            mode=mode,
            rule_set_version=rule_set_version,
        )
        for position, competition in enumerate(candidates, start=1)
    ]


def _reposition(items: list[RankedRecommendation]) -> list[RankedRecommendation]:
    return [
        RankedRecommendation(
            position=position,
            competition=item.competition,
            reason_codes=item.reason_codes,
            reasons=item.reasons,
            mode=item.mode,
            rule_set_version=item.rule_set_version,
        )
        for position, item in enumerate(items, start=1)
    ]
