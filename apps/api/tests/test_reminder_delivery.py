from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionTimeNode,
    Message,
    Reminder,
    ReminderSetting,
    StudentProfile,
    Subscription,
    User,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ReminderStatus,
    SubscriptionStatus,
    UserRole,
)
from competehub_api.services import notifications
from competehub_api.services.engagement import update_subscription
from competehub_api.services.messages import purge_expired_messages
from competehub_api.services.notifications import create_competition_event_message
from competehub_api.services.profiles import update_student_preferences
from competehub_api.services.reminder_delivery import (
    ReminderDeliveryError,
    dispatch_due_reminders,
    requeue_failed_reminders,
)
from competehub_api.timezones import stored_datetime_as_utc


def test_dispatch_due_reminder_creates_one_idempotent_snapshot(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)

        first = dispatch_due_reminders(now=now)
        second = dispatch_due_reminders(now=now)

        assert first == {"dispatched": 1, "cancelled": 0, "failed": 0}
        assert second == {"dispatched": 0, "cancelled": 0, "failed": 0}
        persisted = db.session.get(Reminder, reminder.id)
        assert persisted.status == ReminderStatus.SENT
        assert persisted.attempt_count == 1
        assert persisted.sent_at is not None
        messages = Message.query.filter_by(reminder_id=reminder.id).all()
        assert len(messages) == 1
        assert messages[0].message_type == "reminder_due"
        assert messages[0].idempotency_key == f"reminder_due:{reminder.id}"
        assert messages[0].event_occurred_at == reminder.due_at
        assert messages[0].target_snapshot == {
            "competition_id": reminder.competition_id,
            "competition_title": "Delivery fixture",
            "node_type": "registration_deadline",
            "node_occurs_at": (now + timedelta(days=3)).isoformat(),
            "reason_summary": None,
        }


def test_dispatch_missing_reminder_setting_rolls_back_without_mutating_evidence(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        setting = ReminderSetting.query.filter_by(user_id=reminder.user_id).one()
        db.session.delete(setting)
        db.session.commit()

        with pytest.raises(RuntimeError, match="reminder setting"):
            dispatch_due_reminders(now=now)

        persisted = db.session.get(Reminder, reminder.id)
        assert persisted.status == ReminderStatus.PENDING
        assert persisted.attempt_count == 0
        assert persisted.sent_at is None
        assert persisted.failed_at is None
        assert persisted.last_error_code is None
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 0


def test_requeue_missing_reminder_setting_rolls_back_without_mutating_evidence(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now, due_at=now + timedelta(days=1))
        reminder.status = ReminderStatus.FAILED
        reminder.attempt_count = 1
        reminder.failed_at = now - timedelta(minutes=1)
        reminder.last_error_code = "message_persistence_unavailable"
        reminder.next_attempt_at = now
        setting = ReminderSetting.query.filter_by(user_id=reminder.user_id).one()
        db.session.delete(setting)
        db.session.commit()

        with pytest.raises(RuntimeError, match="reminder setting"):
            requeue_failed_reminders(now=now)

        persisted = db.session.get(Reminder, reminder.id)
        assert persisted.status == ReminderStatus.FAILED
        assert persisted.attempt_count == 1
        assert stored_datetime_as_utc(persisted.failed_at) == now - timedelta(minutes=1)
        assert persisted.last_error_code == "message_persistence_unavailable"
        assert stored_datetime_as_utc(persisted.next_attempt_at) == now
        assert persisted.cancel_reason is None
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 0


def test_transient_failure_requeues_only_when_due_then_dispatches_once(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)

        failed = dispatch_due_reminders(
            now=now,
            deliver=lambda reminder, attempted_at: (_ for _ in ()).throw(
                ReminderDeliveryError("message_persistence_unavailable", retryable=True)
            ),
        )

        assert failed == {"dispatched": 0, "cancelled": 0, "failed": 1}
        persisted = db.session.get(Reminder, reminder.id)
        assert persisted.status == ReminderStatus.FAILED
        assert persisted.attempt_count == 1
        assert persisted.last_error_code == "message_persistence_unavailable"
        assert stored_datetime_as_utc(persisted.failed_at) == now
        assert stored_datetime_as_utc(persisted.next_attempt_at) == now + timedelta(seconds=60)
        assert requeue_failed_reminders(now=now + timedelta(seconds=59)) == {
            "requeued": 0,
            "suppressed": 0,
        }

        requeued = requeue_failed_reminders(now=now + timedelta(seconds=60))
        assert requeued == {"requeued": 1, "suppressed": 0}
        assert db.session.get(Reminder, reminder.id).status == ReminderStatus.PENDING

        dispatched = dispatch_due_reminders(now=now + timedelta(seconds=60))
        assert dispatched == {"dispatched": 1, "cancelled": 0, "failed": 0}
        persisted = db.session.get(Reminder, reminder.id)
        assert persisted.status == ReminderStatus.SENT
        assert persisted.attempt_count == 2
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 1


def test_global_false_to_true_restores_only_the_exact_unattempted_future_plan(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    due_at = now + timedelta(days=1)
    with app.app_context():
        reminder = _seed_due_reminder(now, due_at=due_at)
        student = db.session.get(User, reminder.user_id)

        update_student_preferences(student, {"message_enabled": False})
        disabled = db.session.get(Reminder, reminder.id)
        assert disabled.status == ReminderStatus.CANCELLED
        assert disabled.cancel_reason == "global_reminder_disabled"

        update_student_preferences(student, {"message_enabled": True})

        restored = db.session.get(Reminder, reminder.id)
        assert restored.status == ReminderStatus.PENDING
        assert restored.cancel_reason is None
        assert restored.attempt_count == 0
        assert stored_datetime_as_utc(restored.due_at) == due_at


def test_purged_delivery_message_leaves_durable_sent_markers_terminal(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        student = db.session.get(User, reminder.user_id)
        assert dispatch_due_reminders(now=now) == {
            "dispatched": 1,
            "cancelled": 0,
            "failed": 0,
        }
        message = Message.query.filter_by(reminder_id=reminder.id).one()
        message.retained_until = now
        db.session.commit()

        assert purge_expired_messages(now=now, limit=10) == {"purged": 1}
        update_student_preferences(student, {"message_enabled": False})
        update_student_preferences(student, {"message_enabled": True})

        terminal = db.session.get(Reminder, reminder.id)
        assert terminal.status == ReminderStatus.SENT
        assert terminal.attempt_count == 1
        assert terminal.sent_at is not None
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 0


def test_global_reenable_creates_a_missing_current_revision_plan(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    due_at = now + timedelta(days=1)
    with app.app_context():
        reminder = _seed_due_reminder(now, due_at=due_at)
        student = db.session.get(User, reminder.user_id)
        db.session.delete(reminder)
        db.session.commit()

        update_student_preferences(student, {"message_enabled": False})
        update_student_preferences(student, {"message_enabled": True})

        reminders = Reminder.query.filter_by(user_id=student.id).all()
        assert len(reminders) == 1
        assert reminders[0].status == ReminderStatus.PENDING
        assert reminders[0].logical_node_key == "registration-deadline"
        assert stored_datetime_as_utc(reminders[0].due_at) == due_at


def test_global_toggle_suppresses_retry_without_restoring_failed_evidence(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now, due_at=now + timedelta(days=1))
        student = db.session.get(User, reminder.user_id)
        reminder.status = ReminderStatus.FAILED
        reminder.attempt_count = 1
        reminder.last_error_code = "message_persistence_unavailable"
        reminder.failed_at = now
        reminder.next_attempt_at = now + timedelta(minutes=1)
        db.session.commit()

        update_student_preferences(student, {"message_enabled": False})
        suppressed = db.session.get(Reminder, reminder.id)
        assert suppressed.status == ReminderStatus.FAILED
        assert suppressed.attempt_count == 1
        assert suppressed.last_error_code == "message_persistence_unavailable"
        assert suppressed.failed_at is not None
        assert suppressed.next_attempt_at is None
        assert suppressed.cancel_reason == "global_reminder_disabled"

        update_student_preferences(student, {"message_enabled": True})
        terminal = db.session.get(Reminder, reminder.id)
        assert terminal.status == ReminderStatus.FAILED
        assert terminal.next_attempt_at is None
        assert terminal.cancel_reason == "global_reminder_disabled"


def test_subscription_offset_change_suppresses_retryable_failed_plan(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now, due_at=now + timedelta(days=2))
        student = db.session.get(User, reminder.user_id)
        reminder.status = ReminderStatus.FAILED
        reminder.attempt_count = 1
        reminder.last_error_code = "message_persistence_unavailable"
        reminder.failed_at = now
        reminder.next_attempt_at = now + timedelta(minutes=1)
        original_due_at = reminder.due_at
        db.session.commit()

        update_subscription(
            student,
            reminder.competition_id,
            {
                "reminder_enabled": True,
                "remind_days": 2,
                "node_types": ["registration_deadline"],
            },
        )

        suppressed = db.session.get(Reminder, reminder.id)
        assert suppressed.status == ReminderStatus.FAILED
        assert suppressed.next_attempt_at is None
        assert suppressed.cancel_reason == "subscription_offset_not_future"
        assert suppressed.attempt_count == 1
        assert suppressed.last_error_code == "message_persistence_unavailable"
        assert stored_datetime_as_utc(suppressed.due_at) == stored_datetime_as_utc(original_due_at)


def test_domain_event_time_is_distinct_from_message_creation_and_retention(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        competition = db.session.get(Competition, reminder.competition_id)
        event_occurred_at = now - timedelta(days=30)
        before_creation = datetime.now(UTC)

        message = create_competition_event_message(
            user_id=reminder.user_id,
            competition=competition,
            message_type="competition_time_changed",
            idempotency_key="fixture:delayed-domain-event",
            event_occurred_at=event_occurred_at,
            title_snapshot="Delayed domain event",
            body_snapshot=None,
            reason_summary="Timeline changed.",
        )

        assert stored_datetime_as_utc(message.event_occurred_at) == event_occurred_at
        assert stored_datetime_as_utc(message.created_at) >= before_creation
        assert stored_datetime_as_utc(message.retained_until) == (
            stored_datetime_as_utc(message.created_at) + timedelta(days=365)
        )


def test_real_message_persistence_failure_records_retryable_state_via_savepoint(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        db.session.execute(
            text(
                """
                CREATE TRIGGER fail_message_insert
                BEFORE INSERT ON messages
                BEGIN
                    SELECT RAISE(ABORT, 'simulated message persistence failure');
                END
                """
            )
        )
        db.session.commit()

        result = dispatch_due_reminders(now=now)

        assert result == {"dispatched": 0, "cancelled": 0, "failed": 1}
        failed = db.session.get(Reminder, reminder.id)
        assert failed.status == ReminderStatus.FAILED
        assert failed.attempt_count == 1
        assert failed.last_error_code == "message_persistence_unavailable"
        assert failed.next_attempt_at is not None
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 0


def test_requeued_attempt_stays_failed_when_offset_changes_before_dispatch(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        student = db.session.get(User, reminder.user_id)
        dispatch_due_reminders(
            now=now,
            deliver=lambda reminder, attempted_at: (_ for _ in ()).throw(
                ReminderDeliveryError("message_persistence_unavailable", retryable=True)
            ),
        )
        retry_at = now + timedelta(seconds=60)
        assert requeue_failed_reminders(now=retry_at) == {
            "requeued": 1,
            "suppressed": 0,
        }

        update_subscription(
            student,
            reminder.competition_id,
            {
                "reminder_enabled": True,
                "remind_days": 2,
                "node_types": ["registration_deadline"],
            },
        )

        stopped = db.session.get(Reminder, reminder.id)
        assert stopped.status == ReminderStatus.FAILED
        assert stopped.attempt_count == 1
        assert stopped.failed_at is not None
        assert stopped.last_error_code == "message_persistence_unavailable"
        assert stopped.cancel_reason == "subscription_offset_not_future"
        assert dispatch_due_reminders(now=now + timedelta(days=1)) == {
            "dispatched": 0,
            "cancelled": 0,
            "failed": 0,
        }
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 0


def test_dispatch_recheck_keeps_requeued_revoked_attempt_failed(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        dispatch_due_reminders(
            now=now,
            deliver=lambda reminder, attempted_at: (_ for _ in ()).throw(
                ReminderDeliveryError("message_persistence_unavailable", retryable=True)
            ),
        )
        retry_at = now + timedelta(seconds=60)
        assert requeue_failed_reminders(now=retry_at) == {
            "requeued": 1,
            "suppressed": 0,
        }
        subscription = Subscription.query.filter_by(
            user_id=reminder.user_id,
            competition_id=reminder.competition_id,
        ).one()
        subscription.status = SubscriptionStatus.CANCELLED
        db.session.commit()

        assert dispatch_due_reminders(now=retry_at) == {
            "dispatched": 0,
            "cancelled": 0,
            "failed": 1,
        }
        stopped = db.session.get(Reminder, reminder.id)
        assert stopped.status == ReminderStatus.FAILED
        assert stopped.attempt_count == 1
        assert stopped.failed_at is not None
        assert stopped.last_error_code == "message_persistence_unavailable"
        assert stopped.next_attempt_at is None
        assert stopped.cancel_reason == "subscription_cancelled"
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 0


@pytest.mark.parametrize(
    "error,max_attempts,expected_reason",
    [
        (
            ReminderDeliveryError("delivery_permanent_error", retryable=False),
            3,
            "delivery_permanent_failure",
        ),
        (
            ReminderDeliveryError("message_persistence_unavailable", retryable=True),
            1,
            "delivery_attempts_exhausted",
        ),
    ],
)
def test_permanent_or_exhausted_delivery_failure_is_not_requeued(
    app, error, max_attempts, expected_reason
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    app.config["REMINDER_MAX_ATTEMPTS"] = max_attempts
    with app.app_context():
        reminder = _seed_due_reminder(now)

        result = dispatch_due_reminders(
            now=now,
            deliver=lambda reminder, attempted_at: (_ for _ in ()).throw(error),
        )

        assert result == {"dispatched": 0, "cancelled": 0, "failed": 1}
        terminal = db.session.get(Reminder, reminder.id)
        assert terminal.status == ReminderStatus.FAILED
        assert terminal.attempt_count == 1
        assert terminal.next_attempt_at is None
        assert terminal.cancel_reason == expected_reason


def test_requeue_suppresses_revoked_eligibility_and_preserves_failure_evidence(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        dispatch_due_reminders(
            now=now,
            deliver=lambda reminder, attempted_at: (_ for _ in ()).throw(
                ReminderDeliveryError("message_persistence_unavailable", retryable=True)
            ),
        )
        setting = ReminderSetting.query.filter_by(user_id=reminder.user_id).one()
        setting.enabled = False
        db.session.commit()
        failed_at = db.session.get(Reminder, reminder.id).failed_at

        result = requeue_failed_reminders(now=now + timedelta(seconds=60))

        assert result == {"requeued": 0, "suppressed": 1}
        suppressed = db.session.get(Reminder, reminder.id)
        assert suppressed.status == ReminderStatus.FAILED
        assert suppressed.attempt_count == 1
        assert suppressed.last_error_code == "message_persistence_unavailable"
        assert suppressed.failed_at == failed_at
        assert suppressed.next_attempt_at is None
        assert suppressed.cancel_reason == "global_reminder_disabled"


def test_dispatch_cancels_revoked_pending_plan_without_creating_message(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        subscription = Subscription.query.filter_by(
            user_id=reminder.user_id, competition_id=reminder.competition_id
        ).one()
        subscription.status = SubscriptionStatus.CANCELLED
        db.session.commit()

        result = dispatch_due_reminders(now=now)

        assert result == {"dispatched": 0, "cancelled": 1, "failed": 0}
        stopped = db.session.get(Reminder, reminder.id)
        assert stopped.status == ReminderStatus.CANCELLED
        assert stopped.cancel_reason == "subscription_cancelled"
        assert stopped.attempt_count == 0
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 0


@pytest.mark.parametrize("revocation", ["attempted", "elapsed", "inactive", "unconfirmed"])
def test_global_enable_does_not_restore_ineligible_cancelled_plan(app, revocation) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now, due_at=now + timedelta(days=1))
        student = db.session.get(User, reminder.user_id)
        update_student_preferences(student, {"message_enabled": False})

        if revocation == "attempted":
            reminder.attempt_count = 1
            reminder.last_error_code = "message_persistence_unavailable"
            reminder.failed_at = now
        elif revocation == "elapsed":
            node = db.session.get(CompetitionTimeNode, reminder.time_node_snapshot_id)
            node.occurs_at = now + timedelta(days=2)
        else:
            subscription = Subscription.query.filter_by(
                user_id=reminder.user_id, competition_id=reminder.competition_id
            ).one()
            if revocation == "inactive":
                subscription.status = SubscriptionStatus.CANCELLED
            else:
                subscription.reminder_confirmed_at = None
        db.session.commit()

        update_student_preferences(student, {"message_enabled": True})

        protected = db.session.get(Reminder, reminder.id)
        assert protected.status == ReminderStatus.CANCELLED
        expected_reason = {
            "attempted": "global_reminder_disabled",
            "elapsed": "subscription_offset_not_future",
            "inactive": "subscription_cancelled",
            "unconfirmed": "reminder_disabled",
        }[revocation]
        assert protected.cancel_reason == expected_reason
        assert (
            Reminder.query.filter_by(
                user_id=reminder.user_id, status=ReminderStatus.PENDING
            ).count()
            == 0
        )


def test_global_enable_keeps_prior_revision_cancelled_and_creates_current_plan(app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    due_at = now + timedelta(days=1)
    with app.app_context():
        reminder = _seed_due_reminder(now, due_at=due_at)
        student = db.session.get(User, reminder.user_id)
        update_student_preferences(student, {"message_enabled": False})
        competition = db.session.get(Competition, reminder.competition_id)
        publisher_id = competition.created_by_id
        successor = CompetitionRevision(
            id=510,
            competition=competition,
            revision_number=2,
            revision_status=CompetitionRevisionStatus.APPROVED,
            title=competition.title,
            source_name=competition.source_name,
            source_url=competition.source_url,
            created_by_id=publisher_id,
        )
        current_node = CompetitionTimeNode(
            id=511,
            competition=competition,
            revision=successor,
            logical_node_key=reminder.logical_node_key,
            node_revision=2,
            node_type=reminder.node_type,
            occurs_at=due_at + timedelta(days=3),
            prominence="primary",
        )
        competition.published_revision = successor
        db.session.add_all([successor, current_node])
        db.session.commit()

        update_student_preferences(student, {"message_enabled": True})

        old = db.session.get(Reminder, reminder.id)
        assert old.status == ReminderStatus.CANCELLED
        current = Reminder.query.filter_by(
            user_id=reminder.user_id,
            logical_node_key=reminder.logical_node_key,
            time_node_revision=2,
        ).one()
        assert current.status == ReminderStatus.PENDING
        assert current.time_node_snapshot_id == current_node.id


def test_duplicate_domain_event_conflict_keeps_outer_transaction_atomic(app, monkeypatch) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.app_context():
        reminder = _seed_due_reminder(now)
        competition = db.session.get(Competition, reminder.competition_id)
        existing = create_competition_event_message(
            user_id=reminder.user_id,
            competition=competition,
            message_type="competition_offline",
            idempotency_key="fixture:duplicate-domain-event",
            event_occurred_at=now,
            title_snapshot="First write",
            body_snapshot="First reason",
            reason_summary="First reason",
        )
        db.session.commit()
        existing_id = existing.id
        competition.lifecycle_reason = "Outer lifecycle mutation survives"

        original_get = notifications.engagement_repository.get_message_by_idempotency
        calls = 0

        def miss_once(user_id, idempotency_key):
            nonlocal calls
            calls += 1
            if calls == 1:
                return None
            return original_get(user_id, idempotency_key)

        monkeypatch.setattr(
            notifications.engagement_repository,
            "get_message_by_idempotency",
            miss_once,
        )

        duplicate = create_competition_event_message(
            user_id=reminder.user_id,
            competition=competition,
            message_type="competition_offline",
            idempotency_key="fixture:duplicate-domain-event",
            event_occurred_at=now,
            title_snapshot="Duplicate write",
            body_snapshot="Duplicate reason",
            reason_summary="Duplicate reason",
        )
        db.session.commit()

        assert duplicate.id == existing_id
        assert (
            Message.query.filter_by(
                user_id=reminder.user_id,
                idempotency_key="fixture:duplicate-domain-event",
            ).count()
            == 1
        )
        assert db.session.get(Competition, competition.id).lifecycle_reason == (
            "Outer lifecycle mutation survives"
        )


def _seed_due_reminder(now: datetime, *, due_at: datetime | None = None) -> Reminder:
    due_at = due_at or now
    publisher = User(
        id=501,
        email="delivery-publisher@example.edu",
        password_hash="not-used",
        role=UserRole.ADMIN,
    )
    student = User(
        id=502,
        email="delivery-student@example.edu",
        password_hash="not-used",
        role=UserRole.STUDENT,
    )
    # These fixtures use scalar foreign-key IDs below, so make the referenced
    # users durable before PostgreSQL orders the dependent INSERT statements.
    db.session.add_all([publisher, student])
    db.session.flush()
    competition = Competition(
        id=503,
        title="Delivery fixture",
        source_name="Fixture",
        source_url="https://example.edu/delivery",
        status=CompetitionStatus.PUBLISHED,
        created_by_id=publisher.id,
    )
    revision = CompetitionRevision(
        id=504,
        competition=competition,
        revision_number=1,
        revision_status=CompetitionRevisionStatus.APPROVED,
        title=competition.title,
        source_name=competition.source_name,
        source_url=competition.source_url,
        created_by_id=publisher.id,
    )
    node = CompetitionTimeNode(
        id=505,
        competition=competition,
        revision=revision,
        logical_node_key="registration-deadline",
        node_revision=1,
        node_type="registration_deadline",
        occurs_at=due_at + timedelta(days=3),
        prominence="primary",
    )
    competition.published_revision = revision
    setting = ReminderSetting(
        id=506,
        user=student,
        enabled=True,
        default_remind_days=3,
        node_types=["registration_deadline"],
    )
    profile = StudentProfile(
        id=509,
        user=student,
        interest_tags=[],
        goal_preferences=[],
        blocked_tags=[],
    )
    # The reminder stores only the snapshot's scalar ID. Flush the publication
    # graph first so the unit of work cannot insert that reminder ahead of its
    # time-node row when PostgreSQL enforces the foreign key.
    db.session.add_all([competition, revision, node, setting, profile])
    db.session.flush()
    subscription = Subscription(
        id=507,
        user_id=student.id,
        competition_id=competition.id,
        status=SubscriptionStatus.ACTIVE,
        reminder_enabled=True,
        remind_days=3,
        node_types=["registration_deadline"],
        reminder_confirmed_at=now - timedelta(days=1),
    )
    reminder = Reminder(
        id=508,
        user_id=student.id,
        competition_id=competition.id,
        time_node_snapshot_id=node.id,
        logical_node_key=node.logical_node_key,
        time_node_revision=node.node_revision,
        node_type=node.node_type,
        due_at=due_at,
        title="Registration closes soon",
        body="Review the competition detail.",
        status=ReminderStatus.PENDING,
    )
    db.session.add_all(
        [
            subscription,
            reminder,
        ]
    )
    db.session.commit()
    return reminder
