from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.core.response import success
from app.schemas.recommendation import RecommendationPreferenceSchema
from app.services.recommendation_service import RecommendationService
from app.utils.auth import current_user_id

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.get("")
@jwt_required()
def list_recommendations():
    limit = int(request.args.get("limit", 20))
    return success(RecommendationService.list_recommendations(current_user_id(), limit))


@recommendations_bp.put("/preferences")
@jwt_required()
def update_preferences():
    payload = RecommendationPreferenceSchema().load(request.get_json() or {})
    preference = RecommendationService.update_preferences(current_user_id(), payload)
    return success(preference.to_dict(), "推荐偏好已更新")

