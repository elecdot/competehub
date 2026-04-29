from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.core.response import success
from app.schemas.user import ProfileSchema
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
    return success(profile.to_dict(), "个人画像已更新")

