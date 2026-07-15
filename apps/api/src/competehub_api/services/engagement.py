from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from sqlalchemy.exc import IntegrityError

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionTimeNode,
    Favorite,
    Reminder,
    ReminderSetting,
    Subscription,
    User,
)
from competehub_api.models.enums import (
    CompetitionStatus,
    ReminderStatus,
    SubscriptionStatus,
    UserRole,
)
from competehub_api.repositories import engagement as repository
from competehub_api.services.errors import ServiceError
from competehub_api.subscription_node_types import (
    SUBSCRIPTION_NODE_TYPES,
    canonical_subscription_node_types,
)
from competehub_api.timezones import stored_datetime_as_utc

RESTORABLE_CANCEL_REASONS = frozenset(
    {
        "subscription_cancelled",
        "reminder_disabled",
        "node_type_removed",
        "subscription_offset_not_future",
    }
)


@dataclass(frozen=True)
class FavoriteMutation:
    created: bool


@dataclass(frozen=True)
class SubscriptionMutation:
    subscription: Subscription
    created: bool


def favorite_competition(user: User, competition_id: int) -> FavoriteMutation:
    competition = repository.get_competition(competition_id)
    if competition is None or competition.published_revision_id is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    if competition.status not in {
        CompetitionStatus.PUBLISHED,
        CompetitionStatus.CANCELLED,
        CompetitionStatus.ARCHIVED,
        CompetitionStatus.EXPIRED,
    }:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "competition is unavailable for favorite",
        )

    favorite = repository.get_favorite_for_update(user.id, competition_id)
    created = favorite is None
    if favorite is None:
        db.session.add(
            Favorite(
                id=repository.next_sqlite_id(Favorite),
                user_id=user.id,
                competition_id=competition_id,
                is_active=True,
            )
        )
    else:
        favorite.is_active = True
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        if created and _is_unique_constraint(error, "uq_favorites_user_competition"):
            return FavoriteMutation(created=False)
        raise
    return FavoriteMutation(created=created)


def unfavorite_competition(user: User, competition_id: int) -> None:
    if repository.get_competition(competition_id) is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    favorite = repository.get_favorite_for_update(user.id, competition_id)
    if favorite is not None and favorite.is_active:
        favorite.is_active = False
    db.session.commit()


def subscribe_to_competition(
    user: User, competition_id: int, payload: dict
) -> SubscriptionMutation:
    try:
        payload = _canonical_payload(payload)
        subscription = repository.get_subscription_for_update(user.id, competition_id)
        if subscription is not None and subscription.status == SubscriptionStatus.ACTIVE:
            _required_reminder_setting_for_update(user.id)
            db.session.commit()
            return SubscriptionMutation(subscription=subscription, created=False)

        competition = _published_competition(competition_id)
        nodes = _selected_nodes(competition, payload)
        setting = _required_reminder_setting_for_update(user.id)
        now = datetime.now(UTC)
        created = subscription is None
        if subscription is None:
            subscription = Subscription(
                id=repository.next_sqlite_id(Subscription),
                user_id=user.id,
                competition_id=competition_id,
                status=SubscriptionStatus.ACTIVE,
                reminder_enabled=payload["reminder_enabled"],
                remind_days=payload["remind_days"],
                node_types=payload["node_types"],
                reminder_confirmed_at=now,
            )
            db.session.add(subscription)
        else:
            _apply_consent(subscription, payload, now)
            subscription.status = SubscriptionStatus.ACTIVE

        db.session.flush()
        _reconcile_subscription_reminders(subscription, competition, nodes, now, setting)
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        if created and _is_unique_constraint(error, "uq_subscriptions_user_competition"):
            existing = repository.get_subscription_for_update(user.id, competition_id)
            if existing is not None:
                return SubscriptionMutation(subscription=existing, created=False)
        raise
    except Exception:
        db.session.rollback()
        raise
    return SubscriptionMutation(subscription=subscription, created=created)


def update_subscription(user: User, competition_id: int, payload: dict) -> Subscription:
    try:
        payload = _canonical_payload(payload)
        subscription = repository.get_subscription_for_update(user.id, competition_id)
        if subscription is None:
            raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "subscription not found")
        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ServiceError(
                HTTPStatus.CONFLICT, "engagement_unavailable", "subscription is cancelled"
            )
        setting = _required_reminder_setting_for_update(user.id)
        competition = _published_competition(competition_id)
        nodes = _selected_nodes(competition, payload)
        stored_node_types = canonical_subscription_node_types(subscription.node_types or [])
        if subscription.node_types != stored_node_types:
            subscription.node_types = stored_node_types
        if _same_consent(subscription, payload):
            db.session.commit()
            return subscription

        now = datetime.now(UTC)
        _apply_consent(subscription, payload, now)
        _reconcile_subscription_reminders(subscription, competition, nodes, now, setting)
        db.session.commit()
        return subscription
    except Exception:
        db.session.rollback()
        raise


def cancel_subscription(user: User, competition_id: int) -> None:
    if repository.get_competition(competition_id) is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    subscription = repository.get_subscription_for_update(user.id, competition_id)
    if subscription is not None and subscription.status == SubscriptionStatus.ACTIVE:
        subscription.status = SubscriptionStatus.CANCELLED
        for reminder in repository.list_reminders_for_update(user.id, competition_id):
            if reminder.status == ReminderStatus.PENDING:
                reminder.status = ReminderStatus.CANCELLED
                reminder.cancel_reason = "subscription_cancelled"
    db.session.commit()


def subscription_summary(subscription: Subscription) -> dict:
    pending = [
        reminder
        for reminder in repository.list_reminders(subscription.user_id, subscription.competition_id)
        if reminder.status == ReminderStatus.PENDING
    ]
    pending.sort(key=lambda reminder: (reminder.due_at, reminder.id))
    setting = _required_reminder_setting(subscription.user_id)
    if pending:
        unscheduled_reason = None
    elif not subscription.reminder_enabled or not setting.enabled:
        unscheduled_reason = "reminder_disabled"
    else:
        unscheduled_reason = "no_future_eligible_nodes"
    next_reminder = pending[0] if pending else None
    return {
        "competition_id": subscription.competition_id,
        "status": subscription.status.value,
        "is_subscribed": subscription.status == SubscriptionStatus.ACTIVE,
        "reminder_enabled": subscription.reminder_enabled,
        "remind_days": subscription.remind_days,
        "node_types": canonical_subscription_node_types(subscription.node_types or []),
        "reminder_confirmed_at": (
            stored_datetime_as_utc(subscription.reminder_confirmed_at).isoformat()
            if subscription.reminder_confirmed_at is not None
            else None
        ),
        "scheduled_reminder_count": len(pending),
        "next_reminder_at": (
            stored_datetime_as_utc(next_reminder.due_at).isoformat() if next_reminder else None
        ),
        "unscheduled_reason": unscheduled_reason,
    }


def apply_engagement_state(
    user: User | None, competitions: list[Competition]
) -> dict[int, Subscription]:
    """Attach current-student engagement flags without querying per competition."""
    if user is None or user.role != UserRole.STUDENT or not competitions:
        for competition in competitions:
            competition.is_favorited = False
            competition.is_subscribed = False
        return {}

    competition_ids = [competition.id for competition in competitions]
    favorited_ids = repository.list_active_favorite_competition_ids(user.id, competition_ids)
    subscriptions = {
        subscription.competition_id: subscription
        for subscription in repository.list_subscriptions_for_competitions(user.id, competition_ids)
    }
    for competition in competitions:
        competition.is_favorited = competition.id in favorited_ids
        subscription = subscriptions.get(competition.id)
        competition.is_subscribed = (
            subscription is not None and subscription.status == SubscriptionStatus.ACTIVE
        )
    return subscriptions


def apply_competition_detail_engagement_state(user: User | None, competition: Competition) -> None:
    """Attach the persisted relation summary required to prefill a detail form."""
    subscriptions = apply_engagement_state(user, [competition])
    subscription = subscriptions.get(competition.id)
    competition.subscription_summary = subscription_summary(subscription) if subscription else None


def _published_competition(competition_id: int) -> Competition:
    competition = repository.get_competition(competition_id)
    if competition is None or competition.published_revision_id is None:
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    if competition.status != CompetitionStatus.PUBLISHED:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "competition is unavailable for subscription",
        )
    return competition


def _selected_nodes(competition: Competition, payload: dict) -> list[CompetitionTimeNode]:
    current_nodes = repository.list_current_nodes(competition)
    selectable = [
        node
        for node in current_nodes
        if node.node_type in SUBSCRIPTION_NODE_TYPES and node.occurs_at is not None
    ]
    if not selectable:
        raise ServiceError(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "competition has no eligible reminder nodes",
        )
    if not payload["node_types"]:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "subscription fields are invalid",
            {"field": "node_types"},
        )
    selected = [node for node in selectable if node.node_type in payload["node_types"]]
    found_types = {node.node_type for node in selected}
    if not set(payload["node_types"]).issubset(found_types):
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "subscription fields are invalid",
            {"field": "node_types"},
        )
    return selected


def _same_consent(subscription: Subscription, payload: dict) -> bool:
    return (
        subscription.reminder_enabled == payload["reminder_enabled"]
        and subscription.remind_days == payload["remind_days"]
        and canonical_subscription_node_types(subscription.node_types or [])
        == payload["node_types"]
    )


def _apply_consent(subscription: Subscription, payload: dict, now: datetime) -> None:
    subscription.reminder_enabled = payload["reminder_enabled"]
    subscription.remind_days = payload["remind_days"]
    subscription.node_types = payload["node_types"]
    subscription.reminder_confirmed_at = now


def _canonical_payload(payload: dict) -> dict:
    return {**payload, "node_types": canonical_subscription_node_types(payload["node_types"])}


def _required_reminder_setting_for_update(user_id: int) -> ReminderSetting:
    setting = repository.get_reminder_setting_for_update(user_id)
    if setting is None:
        raise _missing_student_owned_data_error()
    return setting


def _required_reminder_setting(user_id: int) -> ReminderSetting:
    setting = repository.get_reminder_setting(user_id)
    if setting is None:
        raise _missing_student_owned_data_error()
    return setting


def _missing_student_owned_data_error() -> ServiceError:
    return ServiceError(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "internal_server_error",
        "student-owned profile data is missing",
    )


def _reconcile_subscription_reminders(
    subscription: Subscription,
    competition: Competition,
    nodes: list[CompetitionTimeNode],
    now: datetime,
    setting: ReminderSetting | None = None,
) -> None:
    if setting is None:
        setting = _required_reminder_setting_for_update(subscription.user_id)
    reminders = repository.list_reminders_for_update(
        subscription.user_id, subscription.competition_id
    )
    if not subscription.reminder_enabled or not setting.enabled:
        for reminder in reminders:
            if reminder.status == ReminderStatus.PENDING:
                reminder.status = ReminderStatus.CANCELLED
                reminder.cancel_reason = (
                    "reminder_disabled"
                    if not subscription.reminder_enabled
                    else "global_reminder_disabled"
                )
        return

    selected_types = set(subscription.node_types or [])
    current_keys = {
        (node.logical_node_key or f"snapshot-{node.id}", node.node_revision)
        for node in repository.list_current_nodes(competition)
    }
    desired = {}
    for node in nodes:
        if node.occurs_at is None:
            continue
        key = (node.logical_node_key or f"snapshot-{node.id}", node.node_revision)
        desired[key] = (
            node,
            stored_datetime_as_utc(node.occurs_at) - timedelta(days=subscription.remind_days),
        )

    for reminder in reminders:
        if reminder.status != ReminderStatus.PENDING:
            continue
        key = (reminder.logical_node_key, reminder.time_node_revision)
        if key not in current_keys:
            continue
        if reminder.node_type not in selected_types:
            reminder.status = ReminderStatus.CANCELLED
            reminder.cancel_reason = "node_type_removed"
        elif key not in desired or desired[key][1] <= now:
            reminder.status = ReminderStatus.CANCELLED
            reminder.cancel_reason = "subscription_offset_not_future"

    by_key = {
        (reminder.logical_node_key, reminder.time_node_revision): reminder for reminder in reminders
    }
    for key, (node, due_at) in desired.items():
        if due_at <= now:
            continue
        reminder = by_key.get(key)
        if reminder is None:
            db.session.add(_new_reminder(subscription, competition, node, due_at))
        elif reminder.status == ReminderStatus.PENDING:
            _refresh_reminder(reminder, competition, node, due_at)
        elif (
            reminder.status == ReminderStatus.CANCELLED
            and reminder.cancel_reason in RESTORABLE_CANCEL_REASONS
        ):
            reminder.status = ReminderStatus.PENDING
            reminder.cancel_reason = None
            _refresh_reminder(reminder, competition, node, due_at)


def _new_reminder(
    subscription: Subscription,
    competition: Competition,
    node: CompetitionTimeNode,
    due_at: datetime,
) -> Reminder:
    return Reminder(
        id=repository.next_sqlite_id(Reminder),
        user_id=subscription.user_id,
        competition_id=subscription.competition_id,
        time_node_snapshot_id=node.id,
        logical_node_key=node.logical_node_key or f"snapshot-{node.id}",
        time_node_revision=node.node_revision,
        node_type=node.node_type,
        due_at=due_at,
        title=f"{competition.published_revision.title}: {node.node_type}",
        body=node.description,
        status=ReminderStatus.PENDING,
    )


def _refresh_reminder(
    reminder: Reminder, competition: Competition, node: CompetitionTimeNode, due_at: datetime
) -> None:
    reminder.time_node_snapshot_id = node.id
    reminder.node_type = node.node_type
    reminder.due_at = due_at
    reminder.title = f"{competition.published_revision.title}: {node.node_type}"
    reminder.body = node.description


def _is_unique_constraint(error: IntegrityError, name: str) -> bool:
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return constraint_name == name or name in str(error.orig)
