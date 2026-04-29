from app.extensions import db
from app.models.base import SerializerMixin, TimestampMixin


class Favorite(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "competition_id", name="uq_favorite_user_competition"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False, index=True)


class Subscription(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (db.UniqueConstraint("user_id", "competition_id", name="uq_subscription_user_competition"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False, index=True)
    remind_days_before = db.Column(db.Integer, default=3, nullable=False)
    channel = db.Column(db.String(32), default="site", nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)


class ReminderSetting(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "reminder_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    default_days_before = db.Column(db.Integer, default=3, nullable=False)
    site_enabled = db.Column(db.Boolean, default=True, nullable=False)
    email_enabled = db.Column(db.Boolean, default=False, nullable=False)


class Notification(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(64), default="reminder", nullable=False)
    status = db.Column(db.String(32), default="unread", nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)


class BehaviorLog(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "behavior_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    target_type = db.Column(db.String(64), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=True, index=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    extra = db.Column(db.JSON, default=dict, nullable=False)
