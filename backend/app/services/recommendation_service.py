from datetime import datetime

from app.extensions import db
from app.models.competition import Competition
from app.models.engagement import Favorite, Subscription
from app.models.recommendation import RecommendationPreference
from app.models.user import UserProfile


DEFAULT_WEIGHTS = {
    "major": 0.3,
    "interest": 0.25,
    "history": 0.15,
    "grade": 0.15,
    "deadline": 0.1,
    "heat": 0.05,
}


class RecommendationService:
    @staticmethod
    def list_recommendations(user_id: int, limit: int = 20) -> list[dict]:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        preference = RecommendationPreference.query.filter_by(user_id=user_id).first()
        weights = DEFAULT_WEIGHTS | ((preference.weights if preference else {}) or {})
        blocked_tags = set((preference.blocked_tags if preference else []) or [])

        favorite_ids = {
            item.competition_id for item in Favorite.query.filter_by(user_id=user_id).all()
        }
        subscribed_ids = {
            item.competition_id for item in Subscription.query.filter_by(user_id=user_id).all()
        }

        competitions = Competition.query.filter_by(status="published").all()
        results = []
        for competition in competitions:
            if blocked_tags.intersection(set(competition.tags or [])):
                continue
            score, reasons = RecommendationService._score(competition, profile, favorite_ids, subscribed_ids, weights)
            if score > 0:
                item = competition.to_dict()
                item["recommend_score"] = round(score, 4)
                item["recommend_reasons"] = reasons
                results.append(item)

        results.sort(key=lambda item: item["recommend_score"], reverse=True)
        return results[:limit]

    @staticmethod
    def _score(competition: Competition, profile: UserProfile | None, favorite_ids: set[int], subscribed_ids: set[int], weights: dict):
        score = 0.0
        reasons = []
        competition_tags = set(competition.tags or [])

        if profile:
            if profile.major and profile.major in (competition.target_majors or []):
                score += weights["major"]
                reasons.append("与你的专业方向匹配")
            if set(profile.interests or []).intersection(competition_tags):
                score += weights["interest"]
                reasons.append("与你的兴趣标签匹配")
            if profile.grade and profile.grade in (competition.target_grades or []):
                score += weights["grade"]
                reasons.append("适合你当前年级参与")

        if competition.id in favorite_ids or competition.id in subscribed_ids:
            score += weights["history"]
            reasons.append("你曾关注过该赛事")

        if competition.registration_deadline_at:
            days_left = (competition.registration_deadline_at - datetime.utcnow()).days
            if 0 <= days_left <= 14:
                score += weights["deadline"]
                reasons.append("该比赛距离截止时间较近")

        if competition.heat > 20:
            score += weights["heat"]
            reasons.append("该比赛近期关注度较高")

        return score, reasons

    @staticmethod
    def update_preferences(user_id: int, payload: dict) -> RecommendationPreference:
        preference = RecommendationPreference.query.filter_by(user_id=user_id).first()
        if preference is None:
            preference = RecommendationPreference(user_id=user_id)
            db.session.add(preference)
        for key, value in payload.items():
            if hasattr(preference, key):
                setattr(preference, key, value)
        db.session.commit()
        return preference

