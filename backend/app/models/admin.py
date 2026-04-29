from app.extensions import db
from app.models.base import SerializerMixin, TimestampMixin


class ScoreRule(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "score_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_category = db.Column(db.String(64), nullable=True)
    weights = db.Column(db.JSON, default=dict, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    version = db.Column(db.String(32), default="v1", nullable=False)


class ReviewItem(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "review_items"

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(64), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(32), default="pending", nullable=False, index=True)
    submitter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    review_comment = db.Column(db.String(500), nullable=True)


class AdminLog(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "admin_logs"

    id = db.Column(db.Integer, primary_key=True)
    operator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(64), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.JSON, default=dict, nullable=False)

