from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.core.decorators import role_required
from app.core.pagination import get_page_params, pagination_payload
from app.core.response import success
from app.schemas.competition import CompetitionCreateSchema, CompetitionUpdateSchema
from app.services.admin_service import AdminService
from app.services.competition_service import CompetitionService
from app.utils.auth import current_user_id

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/statistics")
@jwt_required()
@role_required("admin")
def statistics():
    return success(AdminService.statistics())


@admin_bp.get("/competitions")
@jwt_required()
@role_required("admin")
def admin_competitions():
    page, page_size = get_page_params()
    query = CompetitionService.list_competitions(request.args, include_unpublished=True)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return success(pagination_payload(pagination))


@admin_bp.post("/competitions")
@jwt_required()
@role_required("admin")
def admin_create_competition():
    payload = CompetitionCreateSchema().load(request.get_json() or {})
    competition = CompetitionService.create_competition(payload, current_user_id(), status="published")
    return success(competition.to_dict(), "赛事已创建", status=201)


@admin_bp.put("/competitions/<int:competition_id>")
@jwt_required()
@role_required("admin")
def admin_update_competition(competition_id: int):
    payload = CompetitionUpdateSchema().load(request.get_json() or {})
    competition = CompetitionService.update_competition(competition_id, payload)
    return success(competition.to_dict(), "赛事已更新")

