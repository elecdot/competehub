from __future__ import annotations

from sqlalchemy import func, select

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionTimeNode,
    Favorite,
    Reminder,
    ReminderSetting,
    Subscription,
)


def get_competition(competition_id: int) -> Competition | None:
    return db.session.get(Competition, competition_id)


def get_favorite_for_update(user_id: int, competition_id: int) -> Favorite | None:
    return db.session.scalar(
        select(Favorite)
        .where(Favorite.user_id == user_id, Favorite.competition_id == competition_id)
        .with_for_update()
    )


def get_subscription_for_update(user_id: int, competition_id: int) -> Subscription | None:
    return db.session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.competition_id == competition_id)
        .with_for_update()
    )


def get_reminder_setting_for_update(user_id: int) -> ReminderSetting | None:
    return db.session.scalar(
        select(ReminderSetting).where(ReminderSetting.user_id == user_id).with_for_update()
    )


def list_reminders_for_update(user_id: int, competition_id: int) -> list[Reminder]:
    return list(
        db.session.scalars(
            select(Reminder)
            .where(Reminder.user_id == user_id, Reminder.competition_id == competition_id)
            .order_by(Reminder.id)
            .with_for_update()
        )
    )


def list_reminders(user_id: int, competition_id: int) -> list[Reminder]:
    return list(
        db.session.scalars(
            select(Reminder)
            .where(Reminder.user_id == user_id, Reminder.competition_id == competition_id)
            .order_by(Reminder.id)
        )
    )


def get_reminder_setting(user_id: int) -> ReminderSetting | None:
    return db.session.scalar(select(ReminderSetting).where(ReminderSetting.user_id == user_id))


def list_current_nodes(competition: Competition) -> list[CompetitionTimeNode]:
    return list(
        db.session.scalars(
            select(CompetitionTimeNode).where(
                CompetitionTimeNode.competition_revision_id == competition.published_revision_id
            )
        )
    )


def next_sqlite_id(model) -> int | None:
    if db.session.get_bind().dialect.name != "sqlite":
        return None
    return db.session.scalar(select(func.coalesce(func.max(model.id), 0) + 1))
