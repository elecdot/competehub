from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.core.pagination import get_page_params, pagination_payload
from app.core.response import success
from app.schemas.competition import CompetitionCreateSchema, CompetitionUpdateSchema
from app.services.competition_service import CompetitionService
from app.utils.auth import current_user_id

competitions_bp = Blueprint("competitions", __name__)


@competitions_bp.get("")
def list_competitions():
    page, page_size = get_page_params()
    query = CompetitionService.list_competitions(request.args)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return success(pagination_payload(pagination))


@competitions_bp.get("/<int:competition_id>")
@jwt_required(optional=True)
def get_competition(competition_id: int):
    identity = get_jwt_identity()
    competition = CompetitionService.get_competition(competition_id, int(identity) if identity else None)
    return success(competition.to_dict())


@competitions_bp.post("")
@jwt_required()
def create_competition():
    payload = CompetitionCreateSchema().load(request.get_json() or {})
    competition = CompetitionService.create_competition(payload, current_user_id())
    return success(competition.to_dict(), "赛事已提交，等待审核", status=201)


@competitions_bp.post("/<int:competition_id>/favorite")
@jwt_required()
def favorite(competition_id: int):
    record = CompetitionService.favorite(current_user_id(), competition_id)
    return success(record.to_dict(), "收藏成功")


@competitions_bp.post("/<int:competition_id>/subscribe")
@jwt_required()
def subscribe(competition_id: int):
    payload = request.get_json() or {}
    record = CompetitionService.subscribe(
        current_user_id(),
        competition_id,
        int(payload.get("remind_days_before", 3)),
    )
    return success(record.to_dict(), "订阅成功")


@competitions_bp.put("/<int:competition_id>")
@jwt_required()
def update_competition(competition_id: int):
    payload = CompetitionUpdateSchema().load(request.get_json() or {})
    competition = CompetitionService.update_competition(competition_id, payload)
    return success(competition.to_dict(), "赛事已更新")

