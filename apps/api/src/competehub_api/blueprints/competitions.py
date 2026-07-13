from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
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
from competehub_api.repositories.competitions import (
    PublicCompetitionQuery,
    get_public_competition,
    search_public_competitions,
)
from competehub_api.schemas.competition_public import (
    competition_list_query_schema,
    public_competition_detail_schema,
    public_competition_page_schema,
    subscription_create_schema,
)
from competehub_api.services.auth import current_user
from competehub_api.timezones import stored_datetime_as_utc

competitions_bp = Blueprint("competitions", __name__)


@competitions_bp.get("/competitions")
def list_competitions():
    try:
        query = competition_list_query_schema.load(request.args.to_dict(flat=True))
    except ValidationError as error:
        return validation_error_response(error, "request query is invalid")

    page = search_public_competitions(PublicCompetitionQuery(**query))
    _apply_engagement_state(page.items)
    return success_response(public_competition_page_schema.dump(page))


@competitions_bp.get("/competitions/<int:competition_id>")
def get_competition_detail(competition_id: int):
    competition = get_public_competition(competition_id)
    if competition is None:
        return error_response(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "competition not found",
        )

    _apply_engagement_state([competition])
    return success_response(public_competition_detail_schema.dump(competition))


@competitions_bp.post("/competitions/<int:competition_id>/favorite")
def favorite_competition(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    competition = db.session.get(Competition, competition_id)
    if competition is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    if competition.published_revision_id is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    if not _favorite_creation_allowed(competition):
        return error_response(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "competition is unavailable for favorite",
        )

    favorite = db.session.scalar(
        select(Favorite)
        .where(Favorite.user_id == user.id, Favorite.competition_id == competition_id)
        .with_for_update()
    )
    created = favorite is None
    if favorite is None:
        favorite = Favorite(
            id=_next_sqlite_id(Favorite),
            user_id=user.id,
            competition_id=competition_id,
            is_active=True,
        )
        db.session.add(favorite)
    elif not favorite.is_active:
        favorite.is_active = True
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if created and constraint_name == "uq_favorites_user_competition":
            favorite = db.session.scalar(
                select(Favorite).where(
                    Favorite.user_id == user.id,
                    Favorite.competition_id == competition_id,
                )
            )
            if favorite is not None:
                return success_response(
                    {"competition_id": competition_id, "is_favorited": True},
                    HTTPStatus.OK,
                )
        raise
    return success_response(
        {"competition_id": competition_id, "is_favorited": True},
        HTTPStatus.CREATED if created else HTTPStatus.OK,
    )


@competitions_bp.delete("/competitions/<int:competition_id>/favorite")
def unfavorite_competition(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    competition = db.session.get(Competition, competition_id)
    if competition is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")

    favorite = db.session.scalar(
        select(Favorite)
        .where(Favorite.user_id == user.id, Favorite.competition_id == competition_id)
        .with_for_update()
    )
    if favorite is not None and favorite.is_active:
        favorite.is_active = False
        db.session.commit()
    return success_response({"competition_id": competition_id, "is_favorited": False})


@competitions_bp.post("/competitions/<int:competition_id>/subscription")
def subscribe_to_competition(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        payload = subscription_create_schema.load(request.get_json(silent=True))
    except ValidationError as error:
        return validation_error_response(error, "subscription fields are invalid")

    subscription = db.session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.competition_id == competition_id)
        .with_for_update()
    )
    if subscription is not None and subscription.status == SubscriptionStatus.ACTIVE:
        return success_response(_subscription_summary(subscription))

    competition = db.session.get(Competition, competition_id)
    if competition is None or competition.published_revision_id is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    if competition.status != CompetitionStatus.PUBLISHED:
        return error_response(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "competition is unavailable for subscription",
        )

    nodes, response = _selected_subscription_nodes(competition, payload)
    if response is not None:
        return response

    now = datetime.now(UTC)
    if subscription is None:
        subscription = Subscription(
            id=_next_sqlite_id(Subscription),
            user_id=user.id,
            competition_id=competition_id,
            status=SubscriptionStatus.ACTIVE,
            reminder_enabled=payload["reminder_enabled"],
            remind_days=payload["remind_days"],
            node_types=payload["node_types"],
            reminder_confirmed_at=now,
        )
        db.session.add(subscription)
        created = True
    else:
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.reminder_enabled = payload["reminder_enabled"]
        subscription.remind_days = payload["remind_days"]
        subscription.node_types = payload["node_types"]
        subscription.reminder_confirmed_at = now
        created = False

    if created:
        try:
            db.session.flush()
        except IntegrityError as error:
            db.session.rollback()
            constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint_name == "uq_subscriptions_user_competition":
                subscription = db.session.scalar(
                    select(Subscription).where(
                        Subscription.user_id == user.id,
                        Subscription.competition_id == competition_id,
                    )
                )
                if subscription is not None:
                    return success_response(_subscription_summary(subscription), HTTPStatus.OK)
            raise

    _reconcile_subscription_reminders(subscription, competition, nodes, now)
    db.session.commit()
    return success_response(
        _subscription_summary(subscription),
        HTTPStatus.CREATED if created else HTTPStatus.OK,
    )


@competitions_bp.patch("/competitions/<int:competition_id>/subscription")
def update_competition_subscription(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        payload = subscription_create_schema.load(request.get_json(silent=True))
    except ValidationError as error:
        return validation_error_response(error, "subscription fields are invalid")

    subscription = db.session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.competition_id == competition_id)
        .with_for_update()
    )
    if subscription is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "subscription not found")
    if subscription.status == SubscriptionStatus.CANCELLED:
        return error_response(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "subscription is cancelled",
        )

    competition = db.session.get(Competition, competition_id)
    if competition is None or competition.published_revision_id is None:
        return error_response(HTTPStatus.NOT_FOUND, "not_found", "competition not found")
    if competition.status != CompetitionStatus.PUBLISHED:
        return error_response(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "competition is unavailable for subscription",
        )
    nodes, response = _selected_subscription_nodes(competition, payload)
    if response is not None:
        return response

    if (
        subscription.reminder_enabled == payload["reminder_enabled"]
        and subscription.remind_days == payload["remind_days"]
        and set(subscription.node_types or []) == set(payload["node_types"])
    ):
        return success_response(_subscription_summary(subscription))

    now = datetime.now(UTC)
    subscription.reminder_enabled = payload["reminder_enabled"]
    subscription.remind_days = payload["remind_days"]
    subscription.node_types = payload["node_types"]
    subscription.reminder_confirmed_at = now
    _reconcile_subscription_reminders(subscription, competition, nodes, now)
    db.session.commit()
    return success_response(_subscription_summary(subscription))


@competitions_bp.delete("/competitions/<int:competition_id>/subscription")
def cancel_competition_subscription(competition_id: int):
    user, response = _require_student()
    if response is not None:
        return response

    subscription = db.session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.competition_id == competition_id)
        .with_for_update()
    )
    if subscription is not None and subscription.status == SubscriptionStatus.ACTIVE:
        subscription.status = SubscriptionStatus.CANCELLED
        for reminder in db.session.scalars(
            select(Reminder).where(
                Reminder.user_id == user.id,
                Reminder.competition_id == competition_id,
                Reminder.status == ReminderStatus.PENDING,
            )
        ):
            reminder.status = ReminderStatus.CANCELLED
            reminder.cancel_reason = "subscription_cancelled"
        db.session.commit()
    return success_response(
        {
            "competition_id": competition_id,
            "status": "cancelled",
            "is_subscribed": False,
        }
    )


def _require_student() -> tuple[User | None, object | None]:
    user = current_user(session)
    if user is None:
        return None, error_response(
            HTTPStatus.UNAUTHORIZED,
            "unauthorized",
            "authentication required",
        )
    if user.role != UserRole.STUDENT:
        return None, error_response(HTTPStatus.FORBIDDEN, "forbidden", "student role required")
    return user, None


def _favorite_creation_allowed(competition: Competition) -> bool:
    return competition.published_revision_id is not None and competition.status in {
        CompetitionStatus.PUBLISHED,
        CompetitionStatus.CANCELLED,
        CompetitionStatus.ARCHIVED,
        CompetitionStatus.EXPIRED,
    }


def _next_sqlite_id(model) -> int | None:
    if db.session.get_bind().dialect.name != "sqlite":
        return None
    return db.session.scalar(select(func.coalesce(func.max(model.id), 0) + 1))


def _selected_subscription_nodes(competition: Competition, payload: dict):
    nodes = list(
        db.session.scalars(
            select(CompetitionTimeNode).where(
                CompetitionTimeNode.competition_revision_id == competition.published_revision_id,
                CompetitionTimeNode.node_type.in_(payload["node_types"]),
            )
        )
    )
    found_node_types = {node.node_type for node in nodes}
    if not set(payload["node_types"]).issubset(found_node_types):
        return None, validation_error_response(
            ValidationError(
                {"node_types": ["Selected node types must exist in the published revision."]}
            ),
            "subscription fields are invalid",
        )
    if not any(node.occurs_at is not None for node in nodes):
        return None, error_response(
            HTTPStatus.CONFLICT,
            "engagement_unavailable",
            "competition has no eligible reminder nodes",
        )
    return nodes, None


def _reconcile_subscription_reminders(
    subscription: Subscription,
    competition: Competition,
    nodes: list[CompetitionTimeNode],
    now: datetime,
) -> None:
    reminders = list(
        db.session.scalars(
            select(Reminder).where(
                Reminder.user_id == subscription.user_id,
                Reminder.competition_id == subscription.competition_id,
            )
        )
    )
    global_reminders_enabled = db.session.scalar(
        select(ReminderSetting.enabled)
        .where(ReminderSetting.user_id == subscription.user_id)
        .with_for_update()
    )
    if not subscription.reminder_enabled or global_reminders_enabled is False:
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
    current_nodes = list(
        db.session.scalars(
            select(CompetitionTimeNode).where(
                CompetitionTimeNode.competition_revision_id == competition.published_revision_id
            )
        )
    )
    current_node_keys = {
        (node.logical_node_key or f"snapshot-{node.id}", node.node_revision)
        for node in current_nodes
    }
    desired_nodes = {}
    for node in nodes:
        if node.occurs_at is None:
            continue
        key = (node.logical_node_key or f"snapshot-{node.id}", node.node_revision)
        due_at = stored_datetime_as_utc(node.occurs_at) - timedelta(days=subscription.remind_days)
        desired_nodes[key] = (node, due_at)

    for reminder in reminders:
        if reminder.status != ReminderStatus.PENDING:
            continue
        key = (reminder.logical_node_key, reminder.time_node_revision)
        if key not in current_node_keys:
            continue
        if reminder.node_type not in selected_types:
            reminder.status = ReminderStatus.CANCELLED
            reminder.cancel_reason = "node_type_removed"
        elif key not in desired_nodes or desired_nodes[key][1] <= now:
            reminder.status = ReminderStatus.CANCELLED
            reminder.cancel_reason = "subscription_offset_not_future"

    reminders_by_key = {
        (reminder.logical_node_key, reminder.time_node_revision): reminder for reminder in reminders
    }
    for key, (node, due_at) in desired_nodes.items():
        if due_at <= now:
            continue
        reminder = reminders_by_key.get(key)
        if reminder is None:
            db.session.add(_new_reminder(subscription, competition, node, due_at))
        elif reminder.status == ReminderStatus.PENDING:
            _refresh_reminder(reminder, competition, node, due_at)


def _new_reminder(
    subscription: Subscription,
    competition: Competition,
    node: CompetitionTimeNode,
    due_at: datetime,
) -> Reminder:
    return Reminder(
        id=_next_sqlite_id(Reminder),
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
    reminder: Reminder,
    competition: Competition,
    node: CompetitionTimeNode,
    due_at: datetime,
) -> None:
    reminder.time_node_snapshot_id = node.id
    reminder.node_type = node.node_type
    reminder.due_at = due_at
    reminder.title = f"{competition.published_revision.title}: {node.node_type}"
    reminder.body = node.description


def _subscription_summary(subscription: Subscription) -> dict:
    pending_reminders = list(
        db.session.scalars(
            select(Reminder)
            .where(
                Reminder.user_id == subscription.user_id,
                Reminder.competition_id == subscription.competition_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .order_by(Reminder.due_at, Reminder.id)
        )
    )
    next_reminder_at = pending_reminders[0].due_at if pending_reminders else None
    global_reminders_enabled = db.session.scalar(
        select(ReminderSetting.enabled).where(ReminderSetting.user_id == subscription.user_id)
    )
    if pending_reminders:
        unscheduled_reason = None
    elif not subscription.reminder_enabled or global_reminders_enabled is False:
        unscheduled_reason = "reminder_disabled"
    else:
        unscheduled_reason = "no_future_eligible_nodes"
    return {
        "competition_id": subscription.competition_id,
        "status": subscription.status.value,
        "is_subscribed": subscription.status == SubscriptionStatus.ACTIVE,
        "reminder_enabled": subscription.reminder_enabled,
        "remind_days": subscription.remind_days,
        "node_types": subscription.node_types or [],
        "reminder_confirmed_at": (
            stored_datetime_as_utc(subscription.reminder_confirmed_at).isoformat()
            if subscription.reminder_confirmed_at is not None
            else None
        ),
        "scheduled_reminder_count": len(pending_reminders),
        "next_reminder_at": (
            stored_datetime_as_utc(next_reminder_at).isoformat()
            if next_reminder_at is not None
            else None
        ),
        "unscheduled_reason": unscheduled_reason,
    }


def _apply_engagement_state(competitions: list[Competition]) -> None:
    user = current_user(session)
    if user is None or user.role != UserRole.STUDENT or not competitions:
        return
    competition_ids = [competition.id for competition in competitions]
    favorited_ids = set(
        db.session.scalars(
            select(Favorite.competition_id).where(
                Favorite.user_id == user.id,
                Favorite.is_active.is_(True),
                Favorite.competition_id.in_(competition_ids),
            )
        )
    )
    subscribed_ids = set(
        db.session.scalars(
            select(Subscription.competition_id).where(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.competition_id.in_(competition_ids),
            )
        )
    )
    for competition in competitions:
        competition.is_favorited = competition.id in favorited_ids
        competition.is_subscribed = competition.id in subscribed_ids
