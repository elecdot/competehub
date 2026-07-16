from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.models import User
from competehub_api.models.enums import UserRole
from competehub_api.repositories.competitions import (
    PublicCompetitionQuery,
    get_public_competition,
)
from competehub_api.schemas.common import load_payload
from competehub_api.schemas.competition_public import (
    competition_list_query_schema,
    outbound_click_schema,
    public_competition_detail_schema,
    public_competition_page_schema,
    subscription_create_schema,
)
from competehub_api.services.auth import current_user
from competehub_api.services.competition_discovery import search_public_competitions
from competehub_api.services.engagement import (
    apply_competition_detail_engagement_state,
    apply_engagement_state,
    cancel_subscription,
    subscription_summary,
)
from competehub_api.services.engagement import (
    favorite_competition as favorite_competition_service,
)
from competehub_api.services.engagement import (
    subscribe_to_competition as subscribe_to_competition_service,
)
from competehub_api.services.engagement import (
    unfavorite_competition as unfavorite_competition_service,
)
from competehub_api.services.engagement import (
    update_subscription as update_subscription_service,
)
from competehub_api.services.errors import ServiceError
from competehub_api.services.outbound_clicks import record_outbound_click

competitions_bp = Blueprint("competitions", __name__)


@competitions_bp.get("/competitions")
def list_competitions():
    try:
        query = competition_list_query_schema.load(request.args.to_dict(flat=True))
    except ValidationError as error:
        return validation_error_response(error, "request query is invalid")

    page = search_public_competitions(PublicCompetitionQuery(**query))
    apply_engagement_state(current_user(session), page.items)
    return success_response(public_competition_page_schema.dump(page))


@competitions_bp.get("/competitions/<int:competition_id>")
def get_competition_detail(competition_id: int):
    competition = get_public_competition(competition_id)
    if competition is None:
        return error_response(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "competition not found",
        )

    apply_competition_detail_engagement_state(current_user(session), competition)
    return success_response(public_competition_detail_schema.dump(competition))


@competitions_bp.post("/competitions/<int:competition_id>/outbound_clicks")
def record_competition_outbound_click(competition_id: int):
    competition = get_public_competition(competition_id)
    if competition is None:
        return error_response(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "competition not found",
        )
    try:
        payload = load_payload(outbound_click_schema, request.get_json(silent=True))
        actor_kind = "authenticated" if current_user(session) is not None else "anonymous"
        record_outbound_click(competition, actor_kind=actor_kind, **payload)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return error_response(error.status_code, error.code, error.message, error.details)

    return success_response({"accepted": True}, HTTPStatus.ACCEPTED)


@competitions_bp.post("/competitions/<int:competition_id>/favorite")
def favorite_competition(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        mutation = favorite_competition_service(user, competition_id)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(
        {"competition_id": competition_id, "is_favorited": True},
        HTTPStatus.CREATED if mutation.created else HTTPStatus.OK,
    )


@competitions_bp.delete("/competitions/<int:competition_id>/favorite")
def unfavorite_competition(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        unfavorite_competition_service(user, competition_id)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response({"competition_id": competition_id, "is_favorited": False})


@competitions_bp.post("/competitions/<int:competition_id>/subscription")
def subscribe_to_competition(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        payload = subscription_create_schema.load(request.get_json(silent=True))
    except ValidationError as error:
        return validation_error_response(error, "subscription fields are invalid")

    try:
        mutation = subscribe_to_competition_service(user, competition_id, payload)
        summary = subscription_summary(mutation.subscription)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(
        summary,
        HTTPStatus.CREATED if mutation.created else HTTPStatus.OK,
    )


@competitions_bp.patch("/competitions/<int:competition_id>/subscription")
def update_competition_subscription(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        payload = subscription_create_schema.load(request.get_json(silent=True))
    except ValidationError as error:
        return validation_error_response(error, "subscription fields are invalid")

    try:
        subscription = update_subscription_service(user, competition_id, payload)
        summary = subscription_summary(subscription)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(summary)


@competitions_bp.delete("/competitions/<int:competition_id>/subscription")
def cancel_competition_subscription(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        cancel_subscription(user, competition_id)
    except ServiceError as error:
        return _service_error_response(error)
    return success_response(
        {
            "competition_id": competition_id,
            "status": "cancelled",
            "is_subscribed": False,
        }
    )


def _require_student() -> tuple[User | None, object | None]:
    user = current_user(session)
    if user is None:
        return None, error_response(
            HTTPStatus.UNAUTHORIZED,
            "unauthorized",
            "authentication required",
        )
    if user.role != UserRole.STUDENT:
        return None, error_response(HTTPStatus.FORBIDDEN, "forbidden", "student role required")
    return user, None


def _service_error_response(error: ServiceError):
    return error_response(error.status_code, error.code, error.message, error.details)
