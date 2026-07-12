from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus

from sqlalchemy import func, select

from competehub_api.extensions import db
from competehub_api.models import AuditLog, Competition, Message, Reminder, Subscription, User
from competehub_api.models.enums import (
    CompetitionStatus,
    ReminderStatus,
    SubscriptionStatus,
)
from competehub_api.services.errors import ServiceError

POST_PUBLICATION_TARGET_STATUSES = {
    CompetitionStatus.OFFLINE,
    CompetitionStatus.ARCHIVED,
    CompetitionStatus.CANCELLED,
    CompetitionStatus.EXPIRED,
}


def maintain_competition_status(
    competition: Competition,
    actor: User,
    target_status: str,
    reason: str,
) -> Competition:
    status = CompetitionStatus(target_status)
    if (
        competition.status != CompetitionStatus.PUBLISHED
        or status not in POST_PUBLICATION_TARGET_STATUSES
    ):
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "conflict",
            "competition cannot change to the requested status",
            {"from_status": competition.status.value, "to_status": status.value},
        )

    previous_status = competition.status
    now = datetime.now(UTC)
    if status in {CompetitionStatus.ARCHIVED, CompetitionStatus.EXPIRED}:
        blocking_nodes = [
            node
            for node in (
                competition.published_revision.time_nodes
                if competition.published_revision is not None
                else []
            )
            if node.occurs_at is not None and _as_utc(node.occurs_at) > now
        ]
        if blocking_nodes:
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "conflict",
                "historical lifecycle requires every public time node to have elapsed",
                {
                    "blocking_nodes": [
                        {
                            "snapshot_id": node.id,
                            "logical_node_key": node.logical_node_key,
                            "node_type": node.node_type,
                            "occurs_at": _as_utc(node.occurs_at).isoformat(),
                        }
                        for node in blocking_nodes
                    ]
                },
            )
    competition.status = status
    competition.lifecycle_reason = reason
    competition.lifecycle_changed_at = now
    impact = _apply_lifecycle_effects(competition, status, now)
    db.session.add(
        AuditLog(
            actor_id=actor.id,
            action=f"competition.{status.value}",
            target_type="competition",
            target_id=competition.id,
            result="success",
            detail={
                "from_status": previous_status.value,
                "to_status": status.value,
                "reason": reason,
                "impact": impact,
            },
        )
    )
    db.session.commit()
    return competition


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def lifecycle_impact(competition: Competition) -> dict:
    subscriptions = list(
        db.session.scalars(
            select(Subscription).where(
                Subscription.competition_id == competition.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
    )
    pending_reminders = list(
        db.session.scalars(
            select(Reminder).where(
                Reminder.competition_id == competition.id,
                Reminder.status == ReminderStatus.PENDING,
            )
        )
    )
    future_nodes = [
        node
        for node in (
            competition.published_revision.time_nodes
            if competition.published_revision is not None
            else []
        )
        if node.occurs_at is not None and _as_utc(node.occurs_at) > datetime.now(UTC)
    ]
    return {
        "affected_active_subscriptions": len(subscriptions),
        "pending_reminders_to_cancel": len(pending_reminders),
        "future_nodes": [
            {
                "snapshot_id": node.id,
                "logical_node_key": node.logical_node_key,
                "node_type": node.node_type,
                "occurs_at": _as_utc(node.occurs_at).isoformat(),
            }
            for node in future_nodes
        ],
        "historical_detail_retained_for": ["cancelled", "archived", "expired"],
        "public_detail_removed_for": ["offline"],
    }


def _apply_lifecycle_effects(
    competition: Competition,
    status: CompetitionStatus,
    now: datetime,
) -> dict:
    impact = lifecycle_impact(competition)
    for reminder in db.session.scalars(
        select(Reminder).where(
            Reminder.competition_id == competition.id,
            Reminder.status == ReminderStatus.PENDING,
        )
    ):
        reminder.status = ReminderStatus.CANCELLED
        reminder.cancel_reason = f"competition_{status.value}"

    if status not in {CompetitionStatus.CANCELLED, CompetitionStatus.OFFLINE}:
        return impact
    message_type = f"competition_{status.value}"
    for subscription in db.session.scalars(
        select(Subscription).where(
            Subscription.competition_id == competition.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    ):
        idempotency_key = f"competition:{competition.id}:{status.value}:{now.isoformat()}"
        db.session.add(
            Message(
                id=_next_pk(Message),
                user_id=subscription.user_id,
                competition_id=competition.id,
                message_type=message_type,
                idempotency_key=idempotency_key,
                event_occurred_at=now,
                title=f"{competition.title} is {status.value}",
                body=competition.lifecycle_reason,
            )
        )
    return impact


def _next_pk(model) -> int | None:
    if db.session.get_bind().dialect.name != "sqlite":
        return None
    return (db.session.scalar(select(func.max(model.id))) or 0) + 1
