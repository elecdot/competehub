from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from flask import current_app
from sqlalchemy import select

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionTimeNode,
    Reminder,
    ReminderSetting,
    Subscription,
)
from competehub_api.models.enums import (
    CompetitionStatus,
    ReminderStatus,
    SubscriptionStatus,
)
from competehub_api.services.notifications import (
    NotificationPersistenceError,
    create_reminder_due_message,
)
from competehub_api.services.reminder_state import revoke_pending_reminder

ReminderDeliverer = Callable[[Reminder, datetime], object]


class ReminderDeliveryError(Exception):
    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class ReminderDataIntegrityError(RuntimeError):
    """Required reminder authority data is missing."""


def dispatch_due_reminders(
    *,
    now: datetime | None = None,
    limit: int | None = None,
    deliver: ReminderDeliverer | None = None,
) -> dict[str, int]:
    try:
        return _dispatch_due_reminders(now=now, limit=limit, deliver=deliver)
    except Exception:
        # A batch is one authority decision. Never leave earlier rows committed or
        # dirty when a later reminder exposes missing authority data.
        db.session.rollback()
        raise


def _dispatch_due_reminders(
    *,
    now: datetime | None = None,
    limit: int | None = None,
    deliver: ReminderDeliverer | None = None,
) -> dict[str, int]:
    now = now or datetime.now(UTC)
    batch_size = limit or current_app.config["REMINDER_DISPATCH_BATCH_SIZE"]
    candidates = list(
        db.session.execute(
            select(Reminder.id, Reminder.competition_id)
            .where(Reminder.status == ReminderStatus.PENDING, Reminder.due_at <= now)
            .order_by(Reminder.due_at, Reminder.id)
            .limit(batch_size)
        )
    )
    result = {"dispatched": 0, "cancelled": 0, "failed": 0}
    deliver = deliver or _deliver_in_app_message
    for reminder_id, competition_id in candidates:
        # Message insertion takes FK locks on the parent competition and reminder.
        # Domain transitions already lock in that order, so dispatch must do the
        # same instead of claiming the leaf first and creating a lock cycle.
        locked_competition_id = db.session.scalar(
            select(Competition.id)
            .where(Competition.id == competition_id)
            .with_for_update(of=Competition, skip_locked=True)
        )
        if locked_competition_id is None:
            continue
        reminder = db.session.scalar(
            select(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PENDING,
                Reminder.due_at <= now,
            )
            .with_for_update(of=Reminder, skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if reminder is None:
            continue
        reason = reminder_delivery_ineligibility(reminder, now=now)
        if reason is not None:
            status = revoke_pending_reminder(reminder, reason)
            result["failed" if status == ReminderStatus.FAILED else "cancelled"] += 1
            continue

        reminder.attempt_count += 1
        try:
            deliver(reminder, now)
        except NotificationPersistenceError:
            _record_delivery_failure(
                reminder,
                ReminderDeliveryError("message_persistence_unavailable", retryable=True),
                now=now,
            )
            result["failed"] += 1
        except ReminderDeliveryError as error:
            _record_delivery_failure(reminder, error, now=now)
            result["failed"] += 1
        else:
            reminder.status = ReminderStatus.SENT
            reminder.sent_at = now
            reminder.next_attempt_at = None
            reminder.last_error_code = None
            reminder.failed_at = None
            reminder.cancel_reason = None
            result["dispatched"] += 1

    db.session.commit()
    return result


def requeue_failed_reminders(
    *,
    now: datetime | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    try:
        return _requeue_failed_reminders(now=now, limit=limit)
    except Exception:
        db.session.rollback()
        raise


def _requeue_failed_reminders(
    *,
    now: datetime | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    now = now or datetime.now(UTC)
    batch_size = limit or current_app.config["REMINDER_DISPATCH_BATCH_SIZE"]
    reminders = list(
        db.session.scalars(
            select(Reminder)
            .where(
                Reminder.status == ReminderStatus.FAILED,
                Reminder.next_attempt_at.is_not(None),
                Reminder.next_attempt_at <= now,
            )
            .order_by(Reminder.next_attempt_at, Reminder.id)
            .limit(batch_size)
            .with_for_update(of=Reminder, skip_locked=True)
            .execution_options(populate_existing=True)
        )
    )
    result = {"requeued": 0, "suppressed": 0}
    for reminder in reminders:
        reason = reminder_delivery_ineligibility(reminder, now=now)
        reminder.next_attempt_at = None
        if reason is not None:
            # Failed delivery evidence is terminal to preference/subscription restoration.
            reminder.cancel_reason = reason
            result["suppressed"] += 1
            continue
        reminder.status = ReminderStatus.PENDING
        reminder.cancel_reason = None
        result["requeued"] += 1

    db.session.commit()
    return result


def reminder_delivery_ineligibility(reminder: Reminder, *, now: datetime) -> str | None:
    """MVCC-only eligibility recheck after the worker owns the leaf Reminder lock."""
    setting = db.session.scalar(
        select(ReminderSetting).where(ReminderSetting.user_id == reminder.user_id)
    )
    if setting is None:
        raise ReminderDataIntegrityError(
            f"required reminder setting is missing for user {reminder.user_id}"
        )
    if not setting.enabled:
        return "global_reminder_disabled"
    subscription = db.session.scalar(
        select(Subscription).where(
            Subscription.user_id == reminder.user_id,
            Subscription.competition_id == reminder.competition_id,
        )
    )
    if subscription is None or subscription.status != SubscriptionStatus.ACTIVE:
        return "subscription_cancelled"
    if not subscription.reminder_enabled or subscription.reminder_confirmed_at is None:
        return "reminder_disabled"
    if reminder.node_type not in (subscription.node_types or []):
        return "node_type_removed"

    competition = db.session.get(Competition, reminder.competition_id)
    if competition is None or competition.status != CompetitionStatus.PUBLISHED:
        status = competition.status.value if competition is not None else "deleted"
        return f"competition_{status}"
    node = db.session.get(CompetitionTimeNode, reminder.time_node_snapshot_id)
    if (
        node is None
        or node.competition_revision_id != competition.published_revision_id
        or node.logical_node_key != reminder.logical_node_key
        or node.node_revision != reminder.time_node_revision
        or node.node_type != reminder.node_type
    ):
        return "competition_revision_superseded"
    if node.occurs_at is None or _as_utc(node.occurs_at) <= _as_utc(now):
        return "node_elapsed"
    expected_due_at = _as_utc(node.occurs_at) - timedelta(days=subscription.remind_days)
    if _as_utc(reminder.due_at) != expected_due_at:
        return "subscription_offset_not_future"
    return None


def _deliver_in_app_message(reminder: Reminder, now: datetime):
    return create_reminder_due_message(reminder, created_at=now)


def _record_delivery_failure(
    reminder: Reminder,
    error: ReminderDeliveryError,
    *,
    now: datetime,
) -> None:
    reminder.status = ReminderStatus.FAILED
    reminder.failed_at = now
    reminder.last_error_code = _controlled_error_code(error.code)
    maximum_attempts = current_app.config["REMINDER_MAX_ATTEMPTS"]
    if error.retryable and reminder.attempt_count < maximum_attempts:
        base_seconds = current_app.config["REMINDER_RETRY_BASE_SECONDS"]
        reminder.next_attempt_at = now + timedelta(
            seconds=base_seconds * (2 ** (reminder.attempt_count - 1))
        )
        reminder.cancel_reason = None
    else:
        reminder.next_attempt_at = None
        reminder.cancel_reason = (
            "delivery_attempts_exhausted" if error.retryable else "delivery_permanent_failure"
        )


def _controlled_error_code(code: str) -> str:
    controlled = {
        "delivery_transient_error",
        "message_persistence_unavailable",
        "delivery_permanent_error",
    }
    return code if code in controlled else "delivery_transient_error"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
