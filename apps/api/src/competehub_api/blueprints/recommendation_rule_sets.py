from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.models import User
from competehub_api.models.enums import UserRole
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
from competehub_api.services.recommendation_rule_set_views import (
    recommendation_rule_set_history,
    recommendation_rule_set_read_model,
)
from competehub_api.services.recommendation_rule_sets import (
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
    return success_response(recommendation_rule_set_read_model(rule_set), HTTPStatus.CREATED)


@recommendation_rule_sets_bp.get("/admin/recommendation_rule_sets")
def list_recommendation_rule_sets():
    actor, response = _require_any_capability(
        "recommendation_editor",
        "recommendation_reviewer",
    )
    if response is not None:
        return response
    del actor
    return success_response(recommendation_rule_set_history())


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
    return success_response(recommendation_rule_set_read_model(rule_set))


@recommendation_rule_sets_bp.post("/admin/recommendation_rule_sets/<int:rule_set_id>/submit_review")
def submit_rule_set(rule_set_id: int):
    actor, response = _require_capability("recommendation_editor")
    if response is not None:
        return response
    try:
        rule_set = submit_recommendation_rule_set(rule_set_id, actor)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(recommendation_rule_set_read_model(rule_set))


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
    return success_response(recommendation_rule_set_read_model(rule_set))


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


def _service_error_response(error: ServiceError):
    return error_response(error.status_code, error.code, error.message, error.details)
