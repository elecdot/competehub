from __future__ import annotations

import unicodedata
from copy import deepcopy
from datetime import datetime
from http import HTTPStatus

from marshmallow import ValidationError
from sqlalchemy import func

from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    RecommendationRule,
    RecommendationRuleSet,
    ReviewRecord,
    User,
)
from competehub_api.models.enums import (
    CompetitionStatus,
    RecommendationRuleSetStatus,
    ReviewStatus,
)
from competehub_api.models.mixins import utc_now
from competehub_api.schemas.recommendation_rule_sets import recommendation_rule_input_schema
from competehub_api.services.competition_discovery import competition_tag_names
from competehub_api.services.errors import ServiceError
from competehub_api.timezones import PRODUCT_TIMEZONE, stored_datetime_as_utc

CLONEABLE_RULE_SET_STATUSES = {
    RecommendationRuleSetStatus.ACTIVE,
    RecommendationRuleSetStatus.REJECTED,
    RecommendationRuleSetStatus.RETURNED,
}
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
REVIEW_ACTIONS = {
    "approve": (RecommendationRuleSetStatus.ACTIVE, ReviewStatus.APPROVED),
    "reject": (RecommendationRuleSetStatus.REJECTED, ReviewStatus.REJECTED),
    "return": (RecommendationRuleSetStatus.RETURNED, ReviewStatus.RETURNED),
}


def clone_recommendation_rule_set(
    source_rule_set_id: int,
    actor: User,
) -> RecommendationRuleSet:
    source = (
        RecommendationRuleSet.query.filter_by(id=source_rule_set_id).with_for_update().one_or_none()
    )
    if source is None:
        raise ServiceError(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "recommendation rule set not found",
        )
    if source.status not in CLONEABLE_RULE_SET_STATUSES:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "recommendation rule set cannot be cloned from its current status",
            {"status": source.status.value},
        )

    # Locking the current active row serializes version allocation for normal
    # governance operations; UNIQUE(version) remains the database backstop.
    RecommendationRuleSet.query.filter_by(
        status=RecommendationRuleSetStatus.ACTIVE
    ).with_for_update().one_or_none()
    next_version = (db.session.query(func.max(RecommendationRuleSet.version)).scalar() or 0) + 1
    base_rule_set_id = (
        source.id
        if source.status == RecommendationRuleSetStatus.ACTIVE
        else source.base_rule_set_id
    )
    draft = RecommendationRuleSet(
        version=next_version,
        status=RecommendationRuleSetStatus.DRAFT,
        created_by_id=actor.id,
        cloned_from_rule_set_id=source.id,
        base_rule_set_id=base_rule_set_id,
        rules=[
            RecommendationRule(
                code=rule.code,
                name=rule.name,
                weight=rule.weight,
                conditions=deepcopy(rule.conditions),
                reason_template=rule.reason_template,
                enabled=rule.enabled,
            )
            for rule in source.rules
        ],
    )
    db.session.add(draft)
    db.session.flush()
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action="recommendation_rule_set.create",
            target_type="recommendation_rule_set",
            target_id=draft.id,
            result="success",
            detail={
                "source_rule_set_id": source.id,
                "base_rule_set_id": base_rule_set_id,
                "version": draft.version,
            },
        )
    )
    db.session.commit()
    return draft


def update_recommendation_rule_set(
    rule_set_id: int,
    actor: User,
    rule_payloads: list[dict],
) -> RecommendationRuleSet:
    rule_set = _get_rule_set_for_update(rule_set_id)
    _require_draft_owner(rule_set, actor)
    validated = _validate_rule_payloads(rule_payloads)

    existing_by_code = {rule.code: rule for rule in rule_set.rules}
    requested_codes = {payload["code"] for payload in validated}
    for code, existing in existing_by_code.items():
        if code not in requested_codes:
            rule_set.rules.remove(existing)
    for payload in validated:
        existing = existing_by_code.get(payload["code"])
        if existing is None:
            rule_set.rules.append(RecommendationRule(**payload))
            continue
        for field in ("name", "weight", "conditions", "reason_template", "enabled"):
            setattr(existing, field, deepcopy(payload[field]))
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action="recommendation_rule_set.update",
            target_type="recommendation_rule_set",
            target_id=rule_set.id,
            result="success",
            detail={
                "version": rule_set.version,
                "rule_codes": [item["code"] for item in validated],
            },
        )
    )
    db.session.commit()
    return rule_set


def submit_recommendation_rule_set(
    rule_set_id: int,
    actor: User,
) -> RecommendationRuleSet:
    rule_set = _get_rule_set_for_update(rule_set_id)
    _require_draft_owner(rule_set, actor)
    _validate_submission_completeness(rule_set)
    base = rule_set.base_rule_set_id and db.session.get(
        RecommendationRuleSet, rule_set.base_rule_set_id
    )
    if base is None:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "recommendation rule set has no immutable governance base",
        )
    if not _has_rule_changes(base, rule_set):
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "recommendation rule set has no changes",
            {"code": "no_changes"},
        )

    rule_set.status = RecommendationRuleSetStatus.PENDING_REVIEW
    rule_set.submitted_by_id = actor.id
    rule_set.submitted_at = utc_now()
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action="recommendation_rule_set.submit_review",
            target_type="recommendation_rule_set",
            target_id=rule_set.id,
            result="success",
            detail={
                "version": rule_set.version,
                "base_rule_set_id": rule_set.base_rule_set_id,
                "status": rule_set.status.value,
            },
        )
    )
    db.session.commit()
    return rule_set


def review_recommendation_rule_set(
    rule_set_id: int,
    actor: User,
    action: str,
    comment: str,
) -> RecommendationRuleSet:
    candidate = _get_rule_set_for_update(rule_set_id)
    if candidate.status != RecommendationRuleSetStatus.PENDING_REVIEW:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "already_decided",
            "recommendation rule set is not pending review",
            {"status": candidate.status.value},
        )
    if candidate.submitted_by_id == actor.id:
        raise ServiceError(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "the submitter cannot review the same recommendation rule set",
        )
    normalized_comment = _validate_review_comment(comment)
    try:
        target_status, review_status = REVIEW_ACTIONS[action]
    except KeyError as error:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "unsupported review action",
            {"allowed_actions": sorted(REVIEW_ACTIONS)},
        ) from error

    base = (
        RecommendationRuleSet.query.filter_by(id=candidate.base_rule_set_id)
        .with_for_update()
        .one_or_none()
    )
    current_active = (
        RecommendationRuleSet.query.filter_by(status=RecommendationRuleSetStatus.ACTIVE)
        .with_for_update()
        .one_or_none()
    )
    if base is None:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "stale_rule_set",
            "recommendation rule-set governance base is missing",
        )
    is_stale = current_active is None or candidate.base_rule_set_id != current_active.id
    if action == "approve" and is_stale:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "stale_rule_set",
            "recommendation rule-set governance base is no longer active",
        )

    difference = build_difference_snapshot(base, candidate)
    impact = build_impact_summary(base, candidate, current_active)
    now = utc_now()
    if action == "approve":
        previous_active = current_active
        previous_active.status = RecommendationRuleSetStatus.RETIRED
        previous_active.retired_at = now
        db.session.flush()
        candidate.status = RecommendationRuleSetStatus.ACTIVE
        candidate.activated_at = now
        impact.update(
            {
                "activation_effect": "replace_active_rule_set",
                "active_version_before": previous_active.version,
                "active_version_after": candidate.version,
                "active_behavior_unchanged_until_activation": False,
            }
        )
    else:
        candidate.status = target_status

    candidate.reviewed_by_id = actor.id
    candidate.review_comment = normalized_comment
    candidate.decided_at = now
    db.session.add(
        ReviewRecord(
            target_type="recommendation_rule_set",
            target_id=candidate.id,
            target_revision=candidate.version,
            submitted_by_id=candidate.submitted_by_id,
            submitted_at=candidate.submitted_at,
            reviewed_by_id=actor.id,
            status=review_status,
            comment=normalized_comment,
            difference_snapshot=difference,
            impact_summary=impact,
            decided_at=now,
        )
    )
    _write_rule_set_audit(
        actor,
        f"recommendation_rule_set.{action}",
        candidate,
        {"version": candidate.version, "comment": normalized_comment},
    )
    if action == "approve":
        _write_rule_set_audit(
            actor,
            "recommendation_rule_set.activate",
            candidate,
            {"version": candidate.version},
        )
        _write_rule_set_audit(
            actor,
            "recommendation_rule_set.retire",
            current_active,
            {"version": current_active.version, "successor_version": candidate.version},
        )
    db.session.commit()
    return candidate


def preview_recommendation_rule_set(
    rule_set_id: int,
    payload: dict,
    evaluation_time: datetime | None = None,
) -> dict:
    rule_set = db.session.get(RecommendationRuleSet, rule_set_id)
    if rule_set is None:
        raise ServiceError(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "recommendation rule set not found",
        )
    rules_by_code = {rule.code: rule for rule in rule_set.rules if rule.enabled}
    scenario = payload["scenario"]
    if scenario == "general" and "general_fallback" not in rules_by_code:
        raise _incomplete_preview_error()
    if scenario == "personalized" and not (set(rules_by_code) & PERSONALIZED_RULE_CODES):
        raise _incomplete_preview_error()

    competition_ids = payload["competition_ids"]
    duplicates = sorted(
        {
            competition_id
            for competition_id in competition_ids
            if competition_ids.count(competition_id) > 1
        }
    )
    unique_ids = sorted(set(competition_ids))
    competitions = Competition.query.filter(Competition.id.in_(unique_ids)).all()
    by_id = {competition.id: competition for competition in competitions}
    not_found = sorted(set(unique_ids) - set(by_id))
    has_revision_pointer = hasattr(Competition, "published_revision_id")
    not_recommendable = sorted(
        competition.id
        for competition in competitions
        if competition.status != CompetitionStatus.PUBLISHED
        or (has_revision_pointer and competition.published_revision_id is None)
    )
    if duplicates or not_found or not_recommendable:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "preview fixtures are invalid",
            {
                "duplicate": duplicates,
                "not_found": not_found,
                "not_recommendable": not_recommendable,
            },
        )

    evaluated_at = evaluation_time or utc_now()
    profile = payload.get("synthetic_profile")
    scored = []
    for competition in sorted(competitions, key=lambda item: item.id):
        matches = _matching_preview_rules(
            rules_by_code,
            scenario,
            profile,
            competition,
            evaluated_at,
        )
        if not matches:
            continue
        ordered_matches = sorted(matches, key=lambda match: _rule_code_sort_key(match[0].code))
        scored.append(
            (
                -sum(rule.weight for rule, _ in ordered_matches),
                competition.id,
                {
                    "competition_id": competition.id,
                    "matched_rule_codes": [rule.code for rule, _ in ordered_matches],
                    "reason_codes": [rule.code for rule, _ in ordered_matches],
                    "reasons": [reason for _, reason in ordered_matches],
                },
            )
        )
    scored.sort(key=lambda item: (item[0], item[1]))
    results = []
    for position, (_, _, item) in enumerate(scored, start=1):
        results.append({"position": position, **item})
    return {
        "rule_set_id": rule_set.id,
        "version": rule_set.version,
        "scenario": scenario,
        "fixture_ids": unique_ids,
        "results": results,
    }


def build_difference_snapshot(
    base: RecommendationRuleSet,
    candidate: RecommendationRuleSet,
) -> dict:
    base_rules = {rule.code: _rule_snapshot(rule) for rule in base.rules}
    candidate_rules = {rule.code: _rule_snapshot(rule) for rule in candidate.rules}
    added_codes = sorted(set(candidate_rules) - set(base_rules), key=_rule_code_sort_key)
    removed_codes = sorted(set(base_rules) - set(candidate_rules), key=_rule_code_sort_key)
    shared_codes = sorted(set(base_rules) & set(candidate_rules), key=_rule_code_sort_key)
    changed_rules = []
    unchanged_rule_count = 0
    fields = ("name", "weight", "conditions", "reason_template", "enabled")
    for code in shared_codes:
        changes = {
            field: {"before": base_rules[code][field], "after": candidate_rules[code][field]}
            for field in fields
            if base_rules[code][field] != candidate_rules[code][field]
        }
        if changes:
            changed_rules.append({"code": code, "changes": changes})
        else:
            unchanged_rule_count += 1
    return {
        "base_rule_set_id": base.id,
        "base_version": base.version,
        "candidate_rule_set_id": candidate.id,
        "candidate_version": candidate.version,
        "added_rules": [candidate_rules[code] for code in added_codes],
        "removed_rules": [base_rules[code] for code in removed_codes],
        "changed_rules": changed_rules,
        "unchanged_rule_count": unchanged_rule_count,
    }


def build_impact_summary(
    base: RecommendationRuleSet,
    candidate: RecommendationRuleSet,
    current_active: RecommendationRuleSet | None,
) -> dict:
    difference = build_difference_snapshot(base, candidate)
    changed_fields = {field for rule in difference["changed_rules"] for field in rule["changes"]}
    has_add_remove = bool(difference["added_rules"] or difference["removed_rules"])
    is_stale = current_active is None or base.id != current_active.id
    return {
        "activation_effect": "blocked_by_stale_base" if is_stale else "pending_activation",
        "base_version": base.version,
        "current_active_version": current_active.version if current_active is not None else None,
        "candidate_version": candidate.version,
        "is_stale": is_stale,
        "enabled_rule_count_before": sum(rule.enabled for rule in base.rules),
        "enabled_rule_count_after": sum(rule.enabled for rule in candidate.rules),
        "added_rule_count": len(difference["added_rules"]),
        "removed_rule_count": len(difference["removed_rules"]),
        "changed_rule_count": len(difference["changed_rules"]),
        "ordering_may_change": has_add_remove
        or bool(changed_fields & {"weight", "conditions", "enabled"}),
        "reasons_may_change": has_add_remove
        or bool(changed_fields & {"conditions", "reason_template", "enabled"}),
        "active_behavior_unchanged_until_activation": True,
        "real_profile_evaluation_performed": False,
    }


def _get_rule_set_for_update(rule_set_id: int) -> RecommendationRuleSet:
    rule_set = RecommendationRuleSet.query.filter_by(id=rule_set_id).with_for_update().one_or_none()
    if rule_set is None:
        raise ServiceError(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "recommendation rule set not found",
        )
    return rule_set


def _require_draft_owner(rule_set: RecommendationRuleSet, actor: User) -> None:
    if rule_set.created_by_id != actor.id:
        raise ServiceError(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "only the draft owner can modify or submit it",
        )
    if rule_set.status != RecommendationRuleSetStatus.DRAFT:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "recommendation rule set is not an editable draft",
            {"status": rule_set.status.value},
        )


def _validate_rule_payloads(rule_payloads: list[dict]) -> list[dict]:
    try:
        validated = recommendation_rule_input_schema.load(rule_payloads, many=True)
    except ValidationError as error:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "recommendation rules are invalid",
            {"invalid_fields": error.messages},
        ) from error
    codes = [item["code"] for item in validated]
    duplicate_codes = sorted({code for code in codes if codes.count(code) > 1})
    if duplicate_codes:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "recommendation rule codes must be unique",
            {"invalid_rule_codes": duplicate_codes},
        )
    return validated


def _validate_submission_completeness(rule_set: RecommendationRuleSet) -> None:
    _validate_rule_payloads([_rule_snapshot(rule) for rule in rule_set.rules])
    rules_by_code = {rule.code: rule for rule in rule_set.rules}
    missing_rule_codes = []
    fallback = rules_by_code.get("general_fallback")
    if fallback is None or not fallback.enabled:
        missing_rule_codes.append("general_fallback")
    if not any(
        rule.enabled for code, rule in rules_by_code.items() if code in PERSONALIZED_RULE_CODES
    ):
        missing_rule_codes.append("personalized_rule")
    if missing_rule_codes:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "recommendation rule set is incomplete",
            {
                "missing_rule_codes": missing_rule_codes,
                "invalid_rule_codes": [],
                "invalid_fields": {},
            },
        )


def _has_rule_changes(base: RecommendationRuleSet, candidate: RecommendationRuleSet) -> bool:
    return {rule.code: _rule_snapshot(rule) for rule in base.rules} != {
        rule.code: _rule_snapshot(rule) for rule in candidate.rules
    }


def _rule_snapshot(rule: RecommendationRule) -> dict:
    return {
        "code": rule.code,
        "name": rule.name,
        "weight": rule.weight,
        "conditions": deepcopy(rule.conditions),
        "reason_template": rule.reason_template,
        "enabled": rule.enabled,
    }


def _rule_code_sort_key(code: str) -> tuple[int, str]:
    return (RULE_CODE_ORDER.get(code, len(RULE_CODE_ORDER)), code)


def _incomplete_preview_error() -> ServiceError:
    return ServiceError(
        HTTPStatus.BAD_REQUEST,
        "validation_error",
        "recommendation rule set is incomplete for the preview scenario",
        {"code": "incomplete_preview_rule_set"},
    )


def _matching_preview_rules(
    rules_by_code: dict[str, RecommendationRule],
    scenario: str,
    profile: dict | None,
    competition: Competition,
    evaluation_time: datetime,
) -> list[tuple[RecommendationRule, str]]:
    if scenario == "general":
        fallback = rules_by_code.get("general_fallback")
        return [(fallback, fallback.reason_template)] if fallback is not None else []

    matches = []
    major_rule = rules_by_code.get("major_match")
    if major_rule is not None and profile["major"] in (competition.suitable_majors or []):
        matches.append((major_rule, _render_reason(major_rule, {"major": profile["major"]})))
    grade_rule = rules_by_code.get("grade_match")
    if grade_rule is not None and profile["grade"] in (competition.suitable_grades or []):
        matches.append((grade_rule, _render_reason(grade_rule, {"grade": profile["grade"]})))
    interest_rule = rules_by_code.get("interest_match")
    matched_interests = sorted(
        set(profile["interest_tags"]) & set(competition_tag_names(competition))
    )
    if interest_rule is not None and matched_interests:
        matches.append(
            (
                interest_rule,
                _render_reason(interest_rule, {"interest_tag": matched_interests[0]}),
            )
        )
    deadline_rule = rules_by_code.get("deadline_urgency")
    deadline_match = _deadline_match(deadline_rule, competition, evaluation_time)
    if deadline_match is not None:
        matches.append((deadline_rule, deadline_match))
    return matches


def _deadline_match(
    rule: RecommendationRule | None,
    competition: Competition,
    evaluation_time: datetime,
) -> str | None:
    if rule is None:
        return None
    evaluation_date = stored_datetime_as_utc(evaluation_time).astimezone(PRODUCT_TIMEZONE).date()
    deadlines = sorted(
        stored_datetime_as_utc(node.due_at).astimezone(PRODUCT_TIMEZONE)
        for node in competition.time_nodes
        if node.node_type == "registration_deadline" and node.due_at is not None
    )
    for deadline in deadlines:
        days_remaining = (deadline.date() - evaluation_date).days
        if 0 <= days_remaining <= rule.conditions["max_days"]:
            return _render_reason(
                rule,
                {
                    "deadline_date": deadline.date().isoformat(),
                    "days_remaining": str(days_remaining),
                },
            )
    return None


def _render_reason(rule: RecommendationRule, values: dict[str, str]) -> str:
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


def _validate_review_comment(comment: str) -> str:
    normalized = comment.strip()
    if not normalized or any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "review comment must be non-empty single-line plain text",
            {"field": "comment"},
        )
    return normalized


def _write_rule_set_audit(
    actor: User,
    action: str,
    rule_set: RecommendationRuleSet,
    detail: dict,
) -> None:
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            target_type="recommendation_rule_set",
            target_id=rule_set.id,
            result="success",
            detail=detail,
        )
    )
