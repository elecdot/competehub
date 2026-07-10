from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.models import User
from competehub_api.models.enums import UserRole
from competehub_api.repositories.competitions import get_competition
from competehub_api.schemas.common import load_payload
from competehub_api.schemas.competition_admin import (
    competition_create_schema,
    competition_review_schema,
    competition_schema,
    competition_status_schema,
    competition_update_schema,
)
from competehub_api.services.auth import current_user
from competehub_api.services.competition_publication import (
    create_draft_competition,
    maintain_competition_status,
    review_competition,
    submit_competition_for_review,
    update_competition,
)
from competehub_api.services.errors import ServiceError

admin_bp = Blueprint("admin", __name__)


@admin_bp.post("/admin/competitions")
def create_competition():
    actor, response = _require_admin()
    if response is not None:
        return response

    try:
        payload = load_payload(competition_create_schema, request.get_json(silent=True))
        competition = create_draft_competition(payload, actor)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response(competition_schema.dump(competition), HTTPStatus.CREATED)


@admin_bp.patch("/admin/competitions/<int:competition_id>")
def update_competition_fields(competition_id: int):
    actor, response = _require_admin()
    if response is not None:
        return response
    competition, response = _get_competition(competition_id)
    if response is not None:
        return response

    try:
        payload = load_payload(competition_update_schema, request.get_json(silent=True))
        competition = update_competition(competition, payload, actor)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response(competition_schema.dump(competition))


@admin_bp.post("/admin/competitions/<int:competition_id>/submit_review")
def submit_review(competition_id: int):
    actor, response = _require_admin()
    if response is not None:
        return response
    competition, response = _get_competition(competition_id)
    if response is not None:
        return response

    try:
        competition = submit_competition_for_review(competition, actor)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response(competition_schema.dump(competition))


@admin_bp.post("/admin/competitions/<int:competition_id>/review")
def review(competition_id: int):
    actor, response = _require_admin()
    if response is not None:
        return response
    competition, response = _get_competition(competition_id)
    if response is not None:
        return response

    try:
        payload = load_payload(competition_review_schema, request.get_json(silent=True))
        competition = review_competition(
            competition,
            actor,
            payload["action"],
            payload.get("comment"),
        )
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response(competition_schema.dump(competition))


@admin_bp.patch("/admin/competitions/<int:competition_id>/status")
def update_competition_status(competition_id: int):
    actor, response = _require_admin()
    if response is not None:
        return response
    competition, response = _get_competition(competition_id)
    if response is not None:
        return response

    try:
        payload = load_payload(competition_status_schema, request.get_json(silent=True))
        competition = maintain_competition_status(
            competition,
            actor,
            payload["status"],
            payload["reason"],
        )
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response(competition_schema.dump(competition))


def _require_admin() -> tuple[User | None, object | None]:
    user = current_user(session.get("user_id"))
    if user is None:
        return None, error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "login is required")
    if user.role != UserRole.ADMIN:
        return None, error_response(HTTPStatus.FORBIDDEN, "forbidden", "admin role is required")
    return user, None


def _get_competition(competition_id: int):
    competition = get_competition(competition_id)
    if competition is None:
        return None, error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    return competition, None


def _service_error_response(error: ServiceError):
    return error_response(
        error.status_code,
        error.code,
        error.message,
        error.details,
    )
