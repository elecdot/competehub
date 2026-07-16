from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, exists, func, or_, select, update

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

RECLASSIFIABLE_CANCEL_REASONS = frozenset(
    {
        "subscription_cancelled",
        "reminder_disabled",
        "node_type_removed",
        "subscription_offset_not_future",
        "global_reminder_disabled",
    }
)


@dataclass(frozen=True)
class MessageQuery:
    page: int = 1
    page_size: int = 20
    read_status: str = "all"
    message_type: str | None = None


@dataclass(frozen=True)
class MessagePage:
    items: list[Message]
    page: int
    page_size: int
    total: int


def get_competition(competition_id: int) -> Competition | None:
    return db.session.get(Competition, competition_id)


def get_competition_for_update(competition_id: int) -> Competition | None:
    return db.session.scalar(
        select(Competition)
        .where(Competition.id == competition_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def list_user_reminder_competitions_for_update(user_id: int) -> list[Competition]:
    """Lock reminder parent competitions before the user's mutable reminder rows."""
    competition_ids = (
        select(Subscription.competition_id.label("competition_id"))
        .where(Subscription.user_id == user_id)
        .union(
            select(Reminder.competition_id.label("competition_id")).where(
                Reminder.user_id == user_id
            )
        )
        .subquery()
    )
    return list(
        db.session.scalars(
            select(Competition)
            .join(competition_ids, competition_ids.c.competition_id == Competition.id)
            .order_by(Competition.id)
            .with_for_update(of=Competition)
            .execution_options(populate_existing=True)
        )
    )


def get_favorite_for_update(user_id: int, competition_id: int) -> Favorite | None:
    return db.session.scalar(
        select(Favorite)
        .where(Favorite.user_id == user_id, Favorite.competition_id == competition_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def get_subscription_for_update(user_id: int, competition_id: int) -> Subscription | None:
    return db.session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.competition_id == competition_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def list_subscriptions_for_user_for_update(user_id: int) -> list[Subscription]:
    return list(
        db.session.scalars(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.competition_id, Subscription.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )


def get_reminder_setting_for_update(user_id: int) -> ReminderSetting | None:
    return db.session.scalar(
        select(ReminderSetting)
        .where(ReminderSetting.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def list_reminders_for_update(user_id: int, competition_id: int) -> list[Reminder]:
    return list(
        db.session.scalars(
            select(Reminder)
            .where(Reminder.user_id == user_id, Reminder.competition_id == competition_id)
            .order_by(Reminder.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )


def list_user_reminders_for_update(user_id: int) -> list[Reminder]:
    return list(
        db.session.scalars(
            select(Reminder)
            .where(Reminder.user_id == user_id)
            .order_by(Reminder.competition_id, Reminder.id)
            .with_for_update()
            .execution_options(populate_existing=True)
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


def list_active_subscriptions_for_competition(
    competition_id: int, *, for_update: bool = False
) -> list[Subscription]:
    statement = (
        select(Subscription)
        .where(
            Subscription.competition_id == competition_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .order_by(Subscription.user_id, Subscription.id)
    )
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return list(db.session.scalars(statement))


def list_pending_reminders_for_competition(
    competition_id: int,
    *,
    snapshot_ids: set[int] | None = None,
) -> list[Reminder]:
    if snapshot_ids is not None and not snapshot_ids:
        return []
    statement = select(Reminder).where(
        Reminder.competition_id == competition_id,
        Reminder.status == ReminderStatus.PENDING,
    )
    if snapshot_ids is not None:
        statement = statement.where(Reminder.time_node_snapshot_id.in_(snapshot_ids))
    statement = statement.order_by(Reminder.id)
    return list(db.session.scalars(statement))


def list_reconcilable_reminders_for_competition_for_update(
    competition_id: int,
    *,
    cancelled_reasons: set[str] | None = None,
) -> list[Reminder]:
    """Lock every reminder a competition transition may mutate in one stable order."""
    mutable_states = [
        Reminder.status == ReminderStatus.PENDING,
        and_(
            Reminder.status == ReminderStatus.FAILED,
            Reminder.next_attempt_at.is_not(None),
        ),
    ]
    if cancelled_reasons:
        mutable_states.append(
            and_(
                Reminder.status == ReminderStatus.CANCELLED,
                Reminder.cancel_reason.in_(cancelled_reasons),
                Reminder.attempt_count == 0,
                Reminder.next_attempt_at.is_(None),
                Reminder.sent_at.is_(None),
                Reminder.failed_at.is_(None),
                Reminder.last_error_code.is_(None),
                ~exists(select(Message.id).where(Message.reminder_id == Reminder.id)),
            )
        )
    return list(
        db.session.scalars(
            select(Reminder)
            .where(
                Reminder.competition_id == competition_id,
                or_(*mutable_states),
            )
            .order_by(Reminder.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )


def list_message_backed_reminder_ids(reminder_ids: set[int]) -> set[int]:
    if not reminder_ids:
        return set()
    return set(
        db.session.scalars(
            select(Message.reminder_id).where(Message.reminder_id.in_(reminder_ids)).distinct()
        )
    )


def get_message_by_idempotency(user_id: int, idempotency_key: str) -> Message | None:
    return db.session.scalar(
        select(Message).where(
            Message.user_id == user_id,
            Message.idempotency_key == idempotency_key,
        )
    )


def list_messages_for_user(user_id: int, query: MessageQuery, *, now: datetime) -> MessagePage:
    filters = [
        Message.user_id == user_id,
        Message.retained_until > now,
    ]
    if query.read_status == "unread":
        filters.append(Message.is_read.is_(False))
    if query.message_type is not None:
        filters.append(Message.message_type == query.message_type)

    total = db.session.scalar(select(func.count(Message.id)).where(*filters)) or 0
    items = list(
        db.session.scalars(
            select(Message)
            .where(*filters)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
    )
    return MessagePage(
        items=items,
        page=query.page,
        page_size=query.page_size,
        total=total,
    )


def count_retained_unread_messages(user_id: int, *, now: datetime) -> int:
    return (
        db.session.scalar(
            select(func.count(Message.id)).where(
                Message.user_id == user_id,
                Message.is_read.is_(False),
                Message.retained_until > now,
            )
        )
        or 0
    )


def get_retained_message_for_update(
    user_id: int, message_id: int, *, now: datetime
) -> Message | None:
    return db.session.scalar(
        select(Message)
        .where(
            Message.id == message_id,
            Message.user_id == user_id,
            Message.retained_until > now,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def mark_all_retained_messages_read(user_id: int, read_at: datetime) -> int:
    result = db.session.execute(
        update(Message)
        .where(
            Message.user_id == user_id,
            Message.is_read.is_(False),
            Message.retained_until > read_at,
        )
        .values(is_read=True, read_at=read_at, updated_at=read_at)
    )
    return result.rowcount or 0


def list_expired_messages_for_update(now: datetime, limit: int) -> list[Message]:
    return list(
        db.session.scalars(
            select(Message)
            .where(Message.retained_until <= now)
            .order_by(Message.retained_until, Message.id)
            .limit(limit)
            .with_for_update(of=Message, skip_locked=True)
            .execution_options(populate_existing=True)
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
