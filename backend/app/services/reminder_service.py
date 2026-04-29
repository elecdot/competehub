from app.extensions import db
from app.models.competition import Competition
from datetime import datetime

from app.models.engagement import Notification, ReminderSetting, Subscription


class ReminderService:
    @staticmethod
    def create_notification(user_id: int, title: str, content: str | None = None, type: str = "system") -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=type,
            status="unread",
            sent_at=datetime.utcnow(),
        )
        db.session.add(notification)
        return notification

    @staticmethod
    def notifications(user_id: int) -> dict:
        query = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc())
        items = query.limit(100).all()
        return {
            "items": [item.to_dict() for item in items],
            "unread": Notification.query.filter_by(user_id=user_id, status="unread").count(),
        }

    @staticmethod
    def mark_read(user_id: int, notification_id: int | None = None) -> None:
        query = Notification.query.filter_by(user_id=user_id)
        if notification_id:
            query = query.filter(Notification.id == notification_id)
        for item in query.all():
            item.status = "read"
        db.session.commit()

    @staticmethod
    def calendar(user_id: int) -> list[dict]:
        subscriptions = Subscription.query.filter_by(user_id=user_id, enabled=True).all()
        competition_ids = [item.competition_id for item in subscriptions]
        competitions = Competition.query.filter(Competition.id.in_(competition_ids)).all() if competition_ids else []
        return [
            {
                "competition_id": item.id,
                "title": item.title,
                "registration_deadline_at": item.registration_deadline_at.isoformat() if item.registration_deadline_at else None,
                "competition_start_at": item.competition_start_at.isoformat() if item.competition_start_at else None,
                "competition_end_at": item.competition_end_at.isoformat() if item.competition_end_at else None,
            }
            for item in competitions
        ]

    @staticmethod
    def update_settings(user_id: int, payload: dict) -> ReminderSetting:
        setting = ReminderSetting.query.filter_by(user_id=user_id).first()
        if setting is None:
            setting = ReminderSetting(user_id=user_id)
            db.session.add(setting)
        for key in ["default_days_before", "site_enabled", "email_enabled"]:
            if key in payload:
                setattr(setting, key, payload[key])
        db.session.commit()
        return setting
