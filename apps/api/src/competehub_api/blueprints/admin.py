from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request, session

from competehub_api.errors import error_response
from competehub_api.extensions import db
from competehub_api.models import User
from competehub_api.models.enums import UserRole
from competehub_api.repositories.competitions import get_competition
from competehub_api.services.competition_publication import (
    ServiceError,
    create_draft_competition,
    review_competition,
    serialize_competition,
    submit_competition_for_review,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.post("/admin/competitions")
def create_competition():
    actor = _require_admin()
    if not isinstance(actor, User):
        return actor

    payload = _json_payload()
    try:
        competition = create_draft_competition(payload, actor)
    except ServiceError as error:
        return _service_error_response(error)

    return _success_response(serialize_competition(competition), HTTPStatus.CREATED)


@admin_bp.post("/admin/competitions/<int:competition_id>/submit_review")
def submit_review(competition_id: int):
    actor = _require_admin()
    if not isinstance(actor, User):
        return actor

    competition = get_competition(competition_id)
    if competition is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")

    try:
        competition = submit_competition_for_review(competition, actor)
    except ServiceError as error:
        return _service_error_response(error)

    return _success_response(serialize_competition(competition))


@admin_bp.post("/admin/competitions/<int:competition_id>/review")
def review(competition_id: int):
    actor = _require_admin()
    if not isinstance(actor, User):
        return actor

    competition = get_competition(competition_id)
    if competition is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")

    payload = _json_payload()
    action = payload.get("action")
    if not isinstance(action, str):
        return error_response(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "review action is required",
            {"missing_fields": ["action"]},
        )

    comment = payload.get("comment")
    if comment is not None and not isinstance(comment, str):
        return error_response(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "review comment must be a string",
            {"field": "comment"},
        )

    try:
        competition = review_competition(competition, actor, action, comment)
    except ServiceError as error:
        return _service_error_response(error)

    return _success_response(serialize_competition(competition))


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _require_admin():
    user_id = session.get("user_id")
    if user_id is None:
        return error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "login is required")

    user = db.session.get(User, user_id)
    if user is None:
        return error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "login is required")
    if user.role != UserRole.ADMIN:
        return error_response(HTTPStatus.FORBIDDEN, "forbidden", "admin role is required")
    return user


def _success_response(data: dict[str, Any], status: int = HTTPStatus.OK):
    return jsonify({"data": data, "error": None}), status


def _service_error_response(error: ServiceError):
    return error_response(
        error.status_code,
        error.code,
        error.message,
        error.details,
    )
