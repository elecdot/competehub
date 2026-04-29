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


@admin_bp.get("/users")
@jwt_required()
@role_required("admin")
def users():
    return success(AdminService.list_users())


@admin_bp.get("/posts")
@jwt_required()
@role_required("admin")
def posts():
    user_id = request.args.get("user_id", type=int)
    return success(AdminService.list_posts(user_id))


@admin_bp.delete("/posts/<int:post_id>")
@jwt_required()
@role_required("admin")
def delete_post(post_id: int):
    post = AdminService.delete_post(post_id)
    return success(post.to_dict() if post else None, "帖子已删除")


@admin_bp.get("/certifications")
@jwt_required()
@role_required("admin")
def certifications():
    return success(AdminService.list_certifications())


@admin_bp.put("/certifications/<int:certification_id>")
@jwt_required()
@role_required("admin")
def review_certification(certification_id: int):
    payload = request.get_json() or {}
    record = AdminService.review_certification(
        certification_id,
        payload.get("status", "approved"),
        current_user_id(),
        payload.get("review_comment"),
    )
    return success(record.to_dict() if record else None, "认证状态已更新")


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
