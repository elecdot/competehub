from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.repositories.competitions import get_public_competition
from competehub_api.schemas.competition_public import (
    competition_list_query_schema,
    public_competition_detail_schema,
    public_competition_page_schema,
)
from competehub_api.services.competition_discovery import (
    CompetitionSearchCriteria,
    search_public_competitions,
)

competitions_bp = Blueprint("competitions", __name__)


@competitions_bp.get("/competitions")
def list_competitions():
    try:
        query = competition_list_query_schema.load(request.args.to_dict(flat=True))
    except ValidationError as error:
        return validation_error_response(error, "request query is invalid")

    page = search_public_competitions(CompetitionSearchCriteria(**query))
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
