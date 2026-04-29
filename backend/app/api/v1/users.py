from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.core.response import success
from app.schemas.user import CertificationCreateSchema, ProfileSchema
from app.services.user_service import UserService
from app.utils.auth import current_user_id

users_bp = Blueprint("users", __name__)


@users_bp.get("/me")
@jwt_required()
def me():
    return success(UserService.get_me(current_user_id()))


@users_bp.put("/me/profile")
@jwt_required()
def update_profile():
    payload = ProfileSchema().load(request.get_json() or {})
    profile = UserService.update_profile(current_user_id(), payload)
    return success(profile, "个人画像已更新")


@users_bp.get("/me/certifications")
@jwt_required()
def certifications():
    return success(UserService.list_certifications(current_user_id(), approved_only=False))


@users_bp.post("/me/certifications")
@jwt_required()
def create_certification():
    payload = CertificationCreateSchema().load(request.get_json() or {})
    record = UserService.create_certification(current_user_id(), payload)
    return success(record.to_dict(), "认证申请已提交", status=201)


@users_bp.get("/matchmaking")
@jwt_required()
def matchmaking():
    return success(UserService.list_matchmaking(current_user_id(), request.args))


@users_bp.post("/<int:user_id>/contact")
@jwt_required()
def contact_user(user_id: int):
    result = UserService.contact_user(current_user_id(), user_id, request.get_json() or {})
    return success(result, "联系请求已发送到对方收件箱")
