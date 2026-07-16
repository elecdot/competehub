from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from http import HTTPStatus
from typing import Any

from competehub_api.models import Competition, RecommendationRule
from competehub_api.services.errors import ServiceError
from competehub_api.timezones import PRODUCT_TIMEZONE, stored_datetime_as_utc

PERSONALIZED_RULE_CODES = {
    "major_match",
    "grade_match",
    "interest_match",
    "deadline_urgency",
}
RULE_CODE_ORDER = {
    "major_match": 0,
    "grade_match": 1,
    "interest_match": 2,
    "deadline_urgency": 3,
    "general_fallback": 4,
}
MAX_PUBLIC_REASONS = 3


class RecommendationMode(StrEnum):
    GENERAL = "general"
    PERSONALIZED = "personalized"


@dataclass(frozen=True)
class RankedRecommendation:
    position: int
    competition: Competition
    reason_codes: tuple[str, ...]
    reasons: tuple[str, ...]
    mode: RecommendationMode
    rule_set_version: int | None


@dataclass(frozen=True)
class _ScoredRecommendation:
    weight: int
    competition: Competition
    reason_codes: tuple[str, ...]
    reasons: tuple[str, ...]


def rank_recommendation_candidates(
    *,
    candidates: Sequence[Competition],
    rules: Sequence[RecommendationRule],
    mode: RecommendationMode,
    profile: Mapping[str, Any] | None,
    evaluation_time: datetime,
    rule_set_version: int | None,
    max_returned_reasons: int | None = MAX_PUBLIC_REASONS,
) -> list[RankedRecommendation]:
    """Evaluate already-discovered candidates without querying or exposing weights."""
    rules_by_code = {rule.code: rule for rule in rules if rule.enabled}
    result_rule_set_version = rule_set_version if mode == RecommendationMode.PERSONALIZED else None
    scored: list[_ScoredRecommendation] = []
    for competition in sorted(candidates, key=lambda item: item.id):
        matches = _matching_rules(
            rules_by_code,
            mode,
            profile,
            competition,
            evaluation_time,
        )
        if not matches:
            continue
        strongest_matches = sorted(
            matches,
            key=lambda match: (-match[0].weight, rule_code_sort_key(match[0].code)),
        )
        if max_returned_reasons is not None:
            strongest_matches = strongest_matches[:max_returned_reasons]
        ordered_matches = sorted(
            strongest_matches,
            key=lambda match: rule_code_sort_key(match[0].code),
        )
        scored.append(
            _ScoredRecommendation(
                weight=sum(rule.weight for rule, _ in matches),
                competition=competition,
                reason_codes=tuple(rule.code for rule, _ in ordered_matches),
                reasons=tuple(reason for _, reason in ordered_matches),
            )
        )
    scored.sort(key=lambda item: (-item.weight, item.competition.id))
    return [
        RankedRecommendation(
            position=position,
            competition=item.competition,
            reason_codes=item.reason_codes,
            reasons=item.reasons,
            mode=mode,
            rule_set_version=result_rule_set_version,
        )
        for position, item in enumerate(scored, start=1)
    ]


def rule_code_sort_key(code: str) -> tuple[int, str]:
    return (RULE_CODE_ORDER.get(code, len(RULE_CODE_ORDER)), code)


def _matching_rules(
    rules_by_code: dict[str, RecommendationRule],
    mode: RecommendationMode,
    profile: Mapping[str, Any] | None,
    competition: Competition,
    evaluation_time: datetime,
) -> list[tuple[RecommendationRule, str]]:
    if mode == RecommendationMode.GENERAL:
        fallback = rules_by_code.get("general_fallback")
        return [(fallback, fallback.reason_template)] if fallback is not None else []
    if profile is None:
        return []

    revision = competition.published_revision
    if revision is None:
        return []
    matches = []
    major_rule = rules_by_code.get("major_match")
    if major_rule is not None and _scope_matches(
        revision.major_scope, revision.suitable_majors, profile["major"]
    ):
        matches.append((major_rule, _render_reason(major_rule, {"major": profile["major"]})))
    grade_rule = rules_by_code.get("grade_match")
    if grade_rule is not None and _scope_matches(
        revision.grade_scope, revision.suitable_grades, profile["grade"]
    ):
        matches.append((grade_rule, _render_reason(grade_rule, {"grade": profile["grade"]})))
    interest_rule = rules_by_code.get("interest_match")
    matched_interests = sorted(
        set(profile["interest_tags"])
        & {link.tag.name for link in revision.tag_links if link.tag is not None}
    )
    if interest_rule is not None and matched_interests:
        matches.append(
            (
                interest_rule,
                _render_reason(interest_rule, {"interest_tag": matched_interests[0]}),
            )
        )
    deadline_rule = rules_by_code.get("deadline_urgency")
    deadline_match = _deadline_match(deadline_rule, revision.time_nodes, evaluation_time)
    if deadline_match is not None:
        matches.append((deadline_rule, deadline_match))
    return matches


def _deadline_match(
    rule: RecommendationRule | None,
    time_nodes: list,
    evaluation_time: datetime,
) -> str | None:
    if rule is None:
        return None
    evaluation_date = stored_datetime_as_utc(evaluation_time).astimezone(PRODUCT_TIMEZONE).date()
    deadlines = sorted(
        stored_datetime_as_utc(node.occurs_at).astimezone(PRODUCT_TIMEZONE)
        for node in time_nodes
        if node.node_type == "registration_deadline" and node.occurs_at is not None
    )
    for deadline in deadlines:
        days_remaining = (deadline.date() - evaluation_date).days
        if rule.conditions["min_days"] <= days_remaining <= rule.conditions["max_days"]:
            return _render_reason(
                rule,
                {
                    "deadline_date": deadline.date().isoformat(),
                    "days_remaining": str(days_remaining),
                },
            )
    return None


def _scope_matches(scope: str | None, values: list | None, profile_value: str) -> bool:
    if scope == "all":
        return True
    return scope == "selected" and profile_value in (values or [])


def _render_reason(rule: RecommendationRule, values: Mapping[str, str]) -> str:
    rendered = rule.reason_template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    if "{" in rendered or "}" in rendered:
        raise ServiceError(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "rule_configuration_error",
            "recommendation reason template could not be rendered",
            {"rule_code": rule.code},
        )
    return rendered
