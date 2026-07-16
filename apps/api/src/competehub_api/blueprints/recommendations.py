from __future__ import annotations

from flask import Blueprint, session

from competehub_api.blueprints.responses import success_response
from competehub_api.schemas.recommendations import recommendation_feed_schema
from competehub_api.services.auth import current_user
from competehub_api.services.engagement import apply_engagement_state
from competehub_api.services.recommendations import recommend_competitions

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.get("/recommendations")
def list_recommendations():
    user = current_user(session)
    feed = recommend_competitions(user)
    apply_engagement_state(user, [item.competition for item in feed.items])
    return success_response(recommendation_feed_schema.dump(feed))
