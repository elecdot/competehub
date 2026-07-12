from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.repositories.competitions import (
    PublicCompetitionQuery,
    get_public_competition,
    search_public_competitions,
)
from competehub_api.schemas.common import load_payload
from competehub_api.schemas.competition_public import (
    competition_list_query_schema,
    outbound_click_schema,
    public_competition_detail_schema,
    public_competition_page_schema,
)
from competehub_api.services.auth import current_user
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
