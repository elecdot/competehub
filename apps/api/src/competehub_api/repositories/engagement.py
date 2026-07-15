from __future__ import annotations

from sqlalchemy import func, select

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionTimeNode,
    Favorite,
    Message,
    Reminder,
    ReminderSetting,
    Subscription,
)
from competehub_api.models.enums import ReminderStatus, SubscriptionStatus


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


def list_active_subscriptions_for_competition(competition_id: int) -> list[Subscription]:
    return list(
        db.session.scalars(
            select(Subscription).where(
                Subscription.competition_id == competition_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
    )


def list_pending_reminders_for_competition(
    competition_id: int,
    *,
    snapshot_ids: set[int] | None = None,
    for_update: bool = False,
) -> list[Reminder]:
    if snapshot_ids is not None and not snapshot_ids:
        return []
    statement = select(Reminder).where(
        Reminder.competition_id == competition_id,
        Reminder.status == ReminderStatus.PENDING,
    )
    if snapshot_ids is not None:
        statement = statement.where(Reminder.time_node_snapshot_id.in_(snapshot_ids))
    if for_update:
        statement = statement.with_for_update()
    return list(db.session.scalars(statement))


def get_message_by_idempotency(user_id: int, idempotency_key: str) -> Message | None:
    return db.session.scalar(
        select(Message).where(
            Message.user_id == user_id,
            Message.idempotency_key == idempotency_key,
        )
    )


def get_reminder_setting(user_id: int) -> ReminderSetting | None:
    return db.session.scalar(select(ReminderSetting).where(ReminderSetting.user_id == user_id))


def list_active_favorite_competition_ids(user_id: int, competition_ids: list[int]) -> set[int]:
    if not competition_ids:
        return set()
    return set(
        db.session.scalars(
            select(Favorite.competition_id).where(
                Favorite.user_id == user_id,
                Favorite.is_active.is_(True),
                Favorite.competition_id.in_(competition_ids),
            )
        )
    )


def list_subscriptions_for_competitions(
    user_id: int, competition_ids: list[int]
) -> list[Subscription]:
    if not competition_ids:
        return []
    return list(
        db.session.scalars(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.competition_id.in_(competition_ids),
            )
        )
    )


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
