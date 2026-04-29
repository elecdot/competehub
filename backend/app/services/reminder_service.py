from app.extensions import db
from app.models.competition import Competition
from app.models.engagement import ReminderSetting, Subscription


class ReminderService:
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

