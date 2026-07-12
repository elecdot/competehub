from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.extensions import db
from competehub_api.models import RecommendationRuleSet, ReviewRecord, User
from competehub_api.models.enums import RecommendationRuleSetStatus, UserRole
from competehub_api.schemas.common import load_payload
from competehub_api.schemas.recommendation_rule_sets import (
    recommendation_rule_set_create_schema,
    recommendation_rule_set_preview_schema,
    recommendation_rule_set_review_schema,
    recommendation_rule_set_update_schema,
)
from competehub_api.services.auth import current_user
from competehub_api.services.authorization import user_has_capability
from competehub_api.services.errors import ServiceError
from competehub_api.services.recommendation_rule_sets import (
    build_difference_snapshot,
    build_impact_summary,
    clone_recommendation_rule_set,
    preview_recommendation_rule_set,
    review_recommendation_rule_set,
    submit_recommendation_rule_set,
    update_recommendation_rule_set,
)

recommendation_rule_sets_bp = Blueprint("recommendation_rule_sets", __name__)


@recommendation_rule_sets_bp.post("/admin/recommendation_rule_sets")
def create_recommendation_rule_set():
    actor, response = _require_capability("recommendation_editor")
    if response is not None:
        return response
    try:
        payload = load_payload(
            recommendation_rule_set_create_schema,
            request.get_json(silent=True),
        )
        rule_set = clone_recommendation_rule_set(payload["source_rule_set_id"], actor)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(_rule_set_read_model(rule_set), HTTPStatus.CREATED)


@recommendation_rule_sets_bp.get("/admin/recommendation_rule_sets")
def list_recommendation_rule_sets():
    actor, response = _require_any_capability(
        "recommendation_editor",
        "recommendation_reviewer",
    )
    if response is not None:
        return response
    del actor
    rule_sets = RecommendationRuleSet.query.order_by(RecommendationRuleSet.version.desc()).all()
    return success_response({"items": [_rule_set_read_model(rule_set) for rule_set in rule_sets]})


@recommendation_rule_sets_bp.patch("/admin/recommendation_rule_sets/<int:rule_set_id>")
def update_rule_set(rule_set_id: int):
    actor, response = _require_capability("recommendation_editor")
    if response is not None:
        return response
    try:
        payload = load_payload(
            recommendation_rule_set_update_schema,
            request.get_json(silent=True),
        )
        rule_set = update_recommendation_rule_set(rule_set_id, actor, payload["rules"])
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(_rule_set_read_model(rule_set))


@recommendation_rule_sets_bp.post("/admin/recommendation_rule_sets/<int:rule_set_id>/submit_review")
def submit_rule_set(rule_set_id: int):
    actor, response = _require_capability("recommendation_editor")
    if response is not None:
        return response
    try:
        rule_set = submit_recommendation_rule_set(rule_set_id, actor)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(_rule_set_read_model(rule_set))


@recommendation_rule_sets_bp.post("/admin/recommendation_rule_sets/<int:rule_set_id>/preview")
def preview_rule_set(rule_set_id: int):
    actor, response = _require_any_capability(
        "recommendation_editor",
        "recommendation_reviewer",
    )
    if response is not None:
        return response
    del actor
    try:
        payload = load_payload(
            recommendation_rule_set_preview_schema,
            request.get_json(silent=True),
        )
        preview = preview_recommendation_rule_set(rule_set_id, payload)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(preview)


@recommendation_rule_sets_bp.post("/admin/recommendation_rule_sets/<int:rule_set_id>/review")
def review_rule_set(rule_set_id: int):
    actor, response = _require_capability("recommendation_reviewer")
    if response is not None:
        return response
    try:
        payload = load_payload(
            recommendation_rule_set_review_schema,
            request.get_json(silent=True),
        )
        rule_set = review_recommendation_rule_set(
            rule_set_id,
            actor,
            payload["action"],
            payload["comment"],
        )
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(_rule_set_read_model(rule_set))


def _require_capability(capability: str) -> tuple[User | None, object | None]:
    user = current_user(session)
    if user is None:
        return None, error_response(
            HTTPStatus.UNAUTHORIZED,
            "unauthorized",
            "login is required",
        )
    if user.role != UserRole.ADMIN or not user_has_capability(user, capability):
        return None, error_response(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "required administrator capability is missing",
            {"required_capability": capability},
        )
    return user, None


def _require_any_capability(*capabilities: str) -> tuple[User | None, object | None]:
    user = current_user(session)
    if user is None:
        return None, error_response(
            HTTPStatus.UNAUTHORIZED,
            "unauthorized",
            "login is required",
        )
    if user.role != UserRole.ADMIN or not any(
        user_has_capability(user, capability) for capability in capabilities
    ):
        return None, error_response(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "required administrator capability is missing",
            {"required_capabilities": list(capabilities)},
        )
    return user, None


def _rule_set_read_model(rule_set: RecommendationRuleSet) -> dict:
    active = RecommendationRuleSet.query.filter_by(
        status=RecommendationRuleSetStatus.ACTIVE
    ).one_or_none()
    cloned_from = (
        db.session.get(RecommendationRuleSet, rule_set.cloned_from_rule_set_id)
        if rule_set.cloned_from_rule_set_id is not None
        else None
    )
    base = (
        db.session.get(RecommendationRuleSet, rule_set.base_rule_set_id)
        if rule_set.base_rule_set_id is not None
        else None
    )
    creator = db.session.get(User, rule_set.created_by_id) if rule_set.created_by_id else None
    decision = ReviewRecord.query.filter_by(
        target_type="recommendation_rule_set",
        target_id=rule_set.id,
        target_revision=rule_set.version,
    ).one_or_none()
    difference = None
    impact = None
    if decision is not None:
        difference = decision.difference_snapshot
        impact = decision.impact_summary
    elif base is not None and rule_set.status == RecommendationRuleSetStatus.PENDING_REVIEW:
        difference = build_difference_snapshot(base, rule_set)
        impact = build_impact_summary(base, rule_set, active)
    is_stale = (
        False
        if rule_set.status == RecommendationRuleSetStatus.ACTIVE
        else base is not None and (active is None or base.id != active.id)
    )
    return {
        "rule_set_id": rule_set.id,
        "version": rule_set.version,
        "status": rule_set.status.value,
        "created_by": (
            {"id": creator.id, "display_name": creator.display_name}
            if creator is not None
            else None
        ),
        "cloned_from_rule_set_id": rule_set.cloned_from_rule_set_id,
        "cloned_from_version": cloned_from.version if cloned_from is not None else None,
        "base_rule_set_id": rule_set.base_rule_set_id,
        "base_version": base.version if base is not None else None,
        "active_rule_set_id": active.id if active is not None else None,
        "active_version": active.version if active is not None else None,
        "is_stale": is_stale,
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


def _service_error_response(error: ServiceError):
    return error_response(error.status_code, error.code, error.message, error.details)
