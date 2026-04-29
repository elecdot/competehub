from app.extensions import db
from app.models.base import SerializerMixin, TimestampMixin


class RecommendationRecord(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "recommendation_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    reasons = db.Column(db.JSON, default=list, nullable=False)
    algorithm_version = db.Column(db.String(32), default="rule-v1", nullable=False)


class RecommendationPreference(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "recommendation_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    preferred_tags = db.Column(db.JSON, default=list, nullable=False)
    blocked_tags = db.Column(db.JSON, default=list, nullable=False)
    preferred_levels = db.Column(db.JSON, default=list, nullable=False)
    weights = db.Column(db.JSON, default=dict, nullable=False)

