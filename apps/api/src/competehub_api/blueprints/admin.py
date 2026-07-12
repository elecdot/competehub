from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.models import User
from competehub_api.models.enums import UserRole
from competehub_api.repositories.competitions import (
    get_competition,
    get_competition_revision,
    get_edition_workspace,
    list_competition_revisions,
    list_competition_series,
    list_edition_workspaces,
)
from competehub_api.schemas.common import load_payload
from competehub_api.schemas.competition_admin import (
    competition_review_schema,
    competition_revision_update_schema,
    competition_schema,
    competition_series_create_schema,
    competition_series_schema,
    competition_status_schema,
    competition_successor_revision_schema,
    edition_create_schema,
)
from competehub_api.services.auth import current_user
from competehub_api.services.competition_publication import (
    maintain_competition_status,
)
from competehub_api.services.competition_revision_views import (
    edition_workspace_read_model,
    edition_workspace_read_models,
    revision_read_model,
    revision_read_models,
)
from competehub_api.services.competition_revisions import (
    create_edition_with_revision,
    create_series,
    create_successor_revision,
    review_revision,
    submit_revision,
    update_revision,
)
from competehub_api.services.errors import ServiceError

admin_bp = Blueprint("admin", __name__)
COMPETITION_WORKBENCH_CAPABILITIES = {
    "competition_editor",
    "competition_reviewer",
    "competition_maintainer",
}


@admin_bp.post("/admin/competitions")
def create_competition():
    actor, response = _require_admin("competition_editor")
    if response is not None:
        return response

    try:
        payload = load_payload(edition_create_schema, request.get_json(silent=True))
        competition = create_edition_with_revision(payload, actor)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response(edition_workspace_read_model(competition), HTTPStatus.CREATED)


@admin_bp.post("/admin/competitions/<int:competition_id>/revisions")
def create_competition_successor_revision(competition_id: int):
    actor, response = _require_admin("competition_editor")
    if response is not None:
        return response
    competition, response = _get_competition(competition_id)
    if response is not None:
        return response
    try:
        payload = load_payload(
            competition_successor_revision_schema,
            request.get_json(silent=True),
        )
        revision = create_successor_revision(competition, actor, payload["reason"])
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(revision_read_model(revision), HTTPStatus.CREATED)


@admin_bp.get("/admin/competition_series")
def get_series_list():
    _, response = _require_competition_workbench()
    if response is not None:
        return response
    return success_response(
        {"items": competition_series_schema.dump(list_competition_series(), many=True)}
    )


@admin_bp.post("/admin/competition_series")
def create_competition_series():
    actor, response = _require_admin("competition_editor")
    if response is not None:
        return response
    try:
        payload = load_payload(competition_series_create_schema, request.get_json(silent=True))
        series = create_series(payload, actor)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(competition_series_schema.dump(series), HTTPStatus.CREATED)


@admin_bp.get("/admin/competitions/<int:competition_id>")
def get_competition_workspace(competition_id: int):
    _, response = _require_competition_workbench()
    if response is not None:
        return response
    edition = get_edition_workspace(competition_id)
    if edition is None or edition.series_id is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition edition not found")
    return success_response(edition_workspace_read_model(edition))


@admin_bp.get("/admin/competitions")
def get_competition_workspaces():
    _, response = _require_competition_workbench()
    if response is not None:
        return response
    return success_response({"items": edition_workspace_read_models(list_edition_workspaces())})


@admin_bp.get("/admin/competition_revisions")
def get_revision_queue():
    _, response = _require_competition_workbench()
    if response is not None:
        return response
    status = request.args.get("status")
    revisions = list_competition_revisions(status)
    return success_response({"items": revision_read_models(revisions)})


@admin_bp.get("/admin/competition_revisions/<int:revision_id>")
def get_revision_detail(revision_id: int):
    _, response = _require_competition_workbench()
    if response is not None:
        return response
    revision = get_competition_revision(revision_id)
    if revision is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    return success_response(revision_read_model(revision))


@admin_bp.patch("/admin/competition_revisions/<int:revision_id>")
def update_competition_revision(revision_id: int):
    actor, response = _require_admin("competition_editor")
    if response is not None:
        return response
    revision = get_competition_revision(revision_id)
    if revision is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    try:
        payload = load_payload(
            competition_revision_update_schema,
            request.get_json(silent=True),
        )
        revision = update_revision(revision, payload, actor)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(revision_read_model(revision))


@admin_bp.post("/admin/competition_revisions/<int:revision_id>/submit_review")
def submit_competition_revision(revision_id: int):
    actor, response = _require_admin("competition_editor")
    if response is not None:
        return response
    revision = get_competition_revision(revision_id)
    if revision is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    try:
        revision = submit_revision(revision, actor)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(revision_read_model(revision))


@admin_bp.post("/admin/competition_revisions/<int:revision_id>/review")
def review_competition_revision(revision_id: int):
    actor, response = _require_admin("competition_reviewer")
    if response is not None:
        return response
    revision = get_competition_revision(revision_id)
    if revision is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition revision not found")
    try:
        payload = load_payload(competition_review_schema, request.get_json(silent=True))
        revision = review_revision(revision, actor, payload["action"], payload["comment"])
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(revision_read_model(revision))


@admin_bp.patch("/admin/competitions/<int:competition_id>/status")
def update_competition_status(competition_id: int):
    actor, response = _require_admin("competition_maintainer")
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


def _require_admin(required_capability: str | None = None) -> tuple[User | None, object | None]:
    user = current_user(session)
    if user is None:
        return None, error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "login is required")
    if user.role != UserRole.ADMIN:
        return None, error_response(HTTPStatus.FORBIDDEN, "forbidden", "admin role is required")
    if required_capability is not None:
        response = _require_capability(user, required_capability)
        if response is not None:
            return None, response
    return user, None


def _require_competition_workbench() -> tuple[User | None, object | None]:
    user, response = _require_admin()
    if response is not None:
        return None, response
    if not COMPETITION_WORKBENCH_CAPABILITIES.intersection(user.capabilities):
        return None, error_response(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "competition workbench capability is required",
        )
    return user, None


def _require_capability(user: User, capability: str):
    if capability not in user.capabilities:
        return error_response(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            f"{capability} capability is required",
        )
    return None


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
