from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from competehub_api.extensions import db
from competehub_api.models import Competition, CompetitionTimeNode, Message, Reminder
from competehub_api.repositories import engagement as engagement_repository

SUPPORTED_MESSAGE_TYPES = frozenset(
    {
        "reminder_due",
        "competition_time_changed",
        "competition_cancelled",
        "competition_offline",
    }
)
NOTIFICATION_TITLE_MAX_LENGTH = 255


class NotificationPersistenceError(Exception):
    """A message write failed inside a recovered per-message savepoint."""


def bounded_title(subject: str, suffix: str = "") -> str:
    """Fit a title into storage while retaining the event-identifying suffix."""
    if len(suffix) > NOTIFICATION_TITLE_MAX_LENGTH:
        raise ValueError("notification title suffix exceeds the storage limit")
    subject_limit = NOTIFICATION_TITLE_MAX_LENGTH - len(suffix)
    return f"{subject[:subject_limit]}{suffix}"


def create_in_app_message(
    *,
    user_id: int,
    competition_id: int,
    message_type: str,
    idempotency_key: str,
    event_occurred_at: datetime,
    title_snapshot: str,
    body_snapshot: str | None,
    target_snapshot: dict,
    reminder_id: int | None = None,
    created_at: datetime | None = None,
) -> Message:
    """Create one immutable message without committing the caller's transaction."""
    if message_type not in SUPPORTED_MESSAGE_TYPES:
        raise ValueError(f"unsupported message type: {message_type}")
    existing = engagement_repository.get_message_by_idempotency(user_id, idempotency_key)
    if existing is not None:
        return existing

    created_at = created_at or datetime.now(UTC)
    message = Message(
        id=engagement_repository.next_sqlite_id(Message),
        user_id=user_id,
        reminder_id=reminder_id,
        competition_id=competition_id,
        message_type=message_type,
        idempotency_key=idempotency_key,
        event_occurred_at=event_occurred_at,
        title_snapshot=bounded_title(title_snapshot),
        body_snapshot=body_snapshot,
        target_snapshot=dict(target_snapshot),
        retained_until=created_at + timedelta(days=current_app.config["MESSAGE_RETENTION_DAYS"]),
        created_at=created_at,
        updated_at=created_at,
    )
    try:
        # The database unique key is the final idempotency authority. The savepoint
        # keeps a duplicate-event race from rolling back the surrounding domain event.
        with db.session.begin_nested():
            db.session.add(message)
            db.session.flush([message])
    except IntegrityError as error:
        existing = engagement_repository.get_message_by_idempotency(user_id, idempotency_key)
        if existing is None:
            if not db.session.is_active:
                raise
            raise NotificationPersistenceError from error
        return existing
    except SQLAlchemyError as error:
        if not db.session.is_active:
            raise
        raise NotificationPersistenceError from error
    return message


def create_reminder_due_message(reminder: Reminder, *, created_at: datetime) -> Message:
    competition = db.session.get(Competition, reminder.competition_id)
    node = db.session.get(CompetitionTimeNode, reminder.time_node_snapshot_id)
    if competition is None or node is None or node.occurs_at is None:
        raise RuntimeError("eligible reminder snapshot facts are missing")
    competition_title = (
        competition.published_revision.title
        if competition.published_revision is not None
        else competition.title
    )
    return create_in_app_message(
        user_id=reminder.user_id,
        reminder_id=reminder.id,
        competition_id=reminder.competition_id,
        message_type="reminder_due",
        idempotency_key=f"reminder_due:{reminder.id}",
        event_occurred_at=reminder.due_at,
        title_snapshot=reminder.title,
        body_snapshot=reminder.body,
        target_snapshot={
            "competition_id": reminder.competition_id,
            "competition_title": competition_title,
            "node_type": reminder.node_type,
            "node_occurs_at": _as_utc(node.occurs_at).isoformat(),
            "reason_summary": None,
        },
        created_at=created_at,
    )


def create_competition_event_message(
    *,
    user_id: int,
    competition: Competition,
    message_type: str,
    idempotency_key: str,
    event_occurred_at: datetime,
    title_snapshot: str,
    body_snapshot: str | None,
    reason_summary: str | None,
) -> Message:
    return create_in_app_message(
        user_id=user_id,
        competition_id=competition.id,
        message_type=message_type,
        idempotency_key=idempotency_key,
        event_occurred_at=event_occurred_at,
        title_snapshot=title_snapshot,
        body_snapshot=body_snapshot,
        target_snapshot={
            "competition_id": competition.id,
            "competition_title": competition.title,
            "node_type": None,
            "node_occurs_at": None,
            "reason_summary": reason_summary,
        },
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
