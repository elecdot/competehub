from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

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
from competehub_api.services.engagement import (
    _reconcile_subscription_reminders,
    apply_competition_detail_engagement_state,
    apply_engagement_state,
    cancel_subscription,
    subscribe_to_competition,
    subscription_summary,
    update_subscription,
)
from competehub_api.services.errors import ServiceError
from competehub_api.services.profiles import update_student_preferences
from competehub_api.timezones import stored_datetime_as_utc


def _payload(**overrides) -> dict:
    payload = {
        "reminder_enabled": True,
        "remind_days": 3,
        "node_types": ["registration_deadline"],
    }
    payload.update(overrides)
    return payload


def test_engagement_read_model_applies_persisted_state_without_writes(
    app, engagement_fixture
) -> None:
    student, competition, subscription, _ = engagement_fixture
    with app.app_context():
        before = (
            db.session.query(Subscription).count(),
            db.session.query(Reminder).count(),
            db.session.query(ReminderSetting).count(),
        )

        apply_engagement_state(student, [competition])
        apply_competition_detail_engagement_state(student, competition)

        assert competition.is_favorited is False
        assert competition.is_subscribed is True
        assert competition.subscription_summary["reminder_enabled"] is True
        assert competition.subscription_summary["remind_days"] == 3
        assert competition.subscription_summary["node_types"] == ["registration_deadline"]
        assert (
            db.session.query(Subscription).count(),
            db.session.query(Reminder).count(),
            db.session.query(ReminderSetting).count(),
        ) == before


@pytest.fixture()
def engagement_fixture(app):
    now = datetime.now(UTC)
    with app.app_context():
        publisher = User(
            id=1, email="publisher@example.edu", password_hash="x", role=UserRole.ADMIN
        )
        student = User(id=2, email="student@example.edu", password_hash="x", role=UserRole.STUDENT)
        competition = Competition(
            id=10,
            title="Reminder service fixture",
            source_name="Fixture",
            source_url="https://example.edu/fixture",
            status=CompetitionStatus.PUBLISHED,
        )
        revision = CompetitionRevision(
            id=20,
            competition=competition,
            revision_number=1,
            revision_status=CompetitionRevisionStatus.APPROVED,
            title="Reminder service fixture",
            source_name="Fixture",
            source_url="https://example.edu/fixture",
            created_by_id=publisher.id,
        )
        competition.published_revision = revision
        node = CompetitionTimeNode(
            id=30,
            competition=competition,
            revision=revision,
            logical_node_key="registration-deadline",
            node_revision=1,
            node_type="registration_deadline",
            occurs_at=now + timedelta(days=20),
            description="Current node",
        )
        subscription = Subscription(
            id=40,
            user_id=student.id,
            competition_id=competition.id,
            status=SubscriptionStatus.ACTIVE,
            reminder_enabled=True,
            remind_days=3,
            node_types=["registration_deadline"],
            reminder_confirmed_at=now,
        )
        setting = ReminderSetting(id=50, user_id=student.id, enabled=True, default_remind_days=3)
        profile = StudentProfile(
            id=50,
            user_id=student.id,
            interest_tags=[],
            goal_preferences=[],
            blocked_tags=[],
        )
        db.session.add_all(
            [publisher, student, competition, revision, node, subscription, setting, profile]
        )
        db.session.commit()
        yield student, competition, subscription, node


@pytest.mark.parametrize("enable_before_resubscribe", [True, False])
def test_global_and_subscription_transitions_handoff_cancel_reason_without_losing_plan(
    app, engagement_fixture, enable_before_resubscribe
) -> None:
    student, competition, _, node = engagement_fixture
    with app.app_context():
        reminder = _current_pending_reminder(student, competition, node)
        db.session.add(reminder)
        db.session.commit()

        update_student_preferences(student, {"message_enabled": False})
        cancel_subscription(student, competition.id)
        cancelled = db.session.get(Reminder, reminder.id)
        assert cancelled.status == ReminderStatus.CANCELLED
        assert cancelled.cancel_reason == "subscription_cancelled"

        if enable_before_resubscribe:
            update_student_preferences(student, {"message_enabled": True})
        subscribe_to_competition(student, competition.id, _payload())
        if not enable_before_resubscribe:
            blocked = db.session.get(Reminder, reminder.id)
            assert blocked.status == ReminderStatus.CANCELLED
            assert blocked.cancel_reason == "global_reminder_disabled"
            update_student_preferences(student, {"message_enabled": True})

        restored = db.session.get(Reminder, reminder.id)
        assert restored.status == ReminderStatus.PENDING
        assert restored.cancel_reason is None
        assert (
            Reminder.query.filter_by(
                user_id=student.id,
                competition_id=competition.id,
                logical_node_key=node.logical_node_key,
                time_node_revision=node.node_revision,
            ).count()
            == 1
        )


@pytest.mark.parametrize("enable_before_consent_restore", [True, False])
def test_global_and_reminder_consent_transitions_handoff_cancel_reason_without_losing_plan(
    app, engagement_fixture, enable_before_consent_restore
) -> None:
    student, competition, _, node = engagement_fixture
    with app.app_context():
        reminder = _current_pending_reminder(student, competition, node)
        db.session.add(reminder)
        db.session.commit()

        update_student_preferences(student, {"message_enabled": False})
        update_subscription(student, competition.id, _payload(reminder_enabled=False))
        disabled = db.session.get(Reminder, reminder.id)
        assert disabled.status == ReminderStatus.CANCELLED
        assert disabled.cancel_reason == "reminder_disabled"

        if enable_before_consent_restore:
            update_student_preferences(student, {"message_enabled": True})
        update_subscription(student, competition.id, _payload(reminder_enabled=True))
        if not enable_before_consent_restore:
            blocked = db.session.get(Reminder, reminder.id)
            assert blocked.status == ReminderStatus.CANCELLED
            assert blocked.cancel_reason == "global_reminder_disabled"
            update_student_preferences(student, {"message_enabled": True})

        restored = db.session.get(Reminder, reminder.id)
        assert restored.status == ReminderStatus.PENDING
        assert restored.cancel_reason is None
        assert (
            Reminder.query.filter_by(
                user_id=student.id,
                competition_id=competition.id,
                logical_node_key=node.logical_node_key,
                time_node_revision=node.node_revision,
            ).count()
            == 1
        )


@pytest.mark.parametrize(
    ("blocker", "expected_reason"),
    [
        ("node_type", "node_type_removed"),
        ("offset", "subscription_offset_not_future"),
    ],
)
@pytest.mark.parametrize("enable_before_semantic_restore", [True, False])
def test_global_and_semantic_subscription_blockers_handoff_without_losing_plan(
    app,
    engagement_fixture,
    blocker,
    expected_reason,
    enable_before_semantic_restore,
) -> None:
    student, competition, _, node = engagement_fixture
    with app.app_context():
        reminder = _current_pending_reminder(student, competition, node)
        db.session.add(reminder)
        if blocker == "node_type":
            db.session.add(
                CompetitionTimeNode(
                    id=31,
                    competition_id=competition.id,
                    competition_revision_id=competition.published_revision_id,
                    logical_node_key="submission-deadline",
                    node_revision=1,
                    node_type="submission_deadline",
                    occurs_at=datetime.now(UTC) + timedelta(days=25),
                )
            )
        db.session.commit()

        update_student_preferences(student, {"message_enabled": False})
        blocked_payload = (
            _payload(node_types=["submission_deadline"])
            if blocker == "node_type"
            else _payload(remind_days=30)
        )
        update_subscription(student, competition.id, blocked_payload)
        blocked = db.session.get(Reminder, reminder.id)
        assert blocked.status == ReminderStatus.CANCELLED
        assert blocked.cancel_reason == expected_reason

        if enable_before_semantic_restore:
            update_student_preferences(student, {"message_enabled": True})
        update_subscription(student, competition.id, _payload())
        if not enable_before_semantic_restore:
            globally_blocked = db.session.get(Reminder, reminder.id)
            assert globally_blocked.status == ReminderStatus.CANCELLED
            assert globally_blocked.cancel_reason == "global_reminder_disabled"
            update_student_preferences(student, {"message_enabled": True})

        restored = db.session.get(Reminder, reminder.id)
        assert restored.status == ReminderStatus.PENDING
        assert restored.cancel_reason is None
        assert (
            Reminder.query.filter_by(
                user_id=student.id,
                competition_id=competition.id,
                logical_node_key=node.logical_node_key,
                time_node_revision=node.node_revision,
            ).count()
            == 1
        )


@pytest.mark.parametrize("path", ["global_enable", "cancel_resubscribe"])
def test_linked_delivery_evidence_prevents_global_restore_and_reason_handoff(
    app, engagement_fixture, path
) -> None:
    student, competition, _, node = engagement_fixture
    with app.app_context():
        reminder = _current_pending_reminder(student, competition, node)
        db.session.add(reminder)
        db.session.commit()

        update_student_preferences(student, {"message_enabled": False})
        db.session.add(
            Message(
                id=70,
                user_id=student.id,
                reminder_id=reminder.id,
                competition_id=competition.id,
                message_type="reminder_due",
                idempotency_key=f"reminder_due:{reminder.id}",
                event_occurred_at=reminder.due_at,
                title_snapshot="Delivered evidence",
                body_snapshot=None,
                target_snapshot={
                    "competition_id": competition.id,
                    "competition_title": competition.title,
                    "node_type": node.node_type,
                    "node_occurs_at": stored_datetime_as_utc(node.occurs_at).isoformat(),
                    "reason_summary": None,
                },
                retained_until=datetime.now(UTC) + timedelta(days=365),
            )
        )
        db.session.commit()

        if path == "cancel_resubscribe":
            cancel_subscription(student, competition.id)
            assert db.session.get(Reminder, reminder.id).cancel_reason == (
                "global_reminder_disabled"
            )
            subscribe_to_competition(student, competition.id, _payload())
        update_student_preferences(student, {"message_enabled": True})

        protected = db.session.get(Reminder, reminder.id)
        assert protected.status == ReminderStatus.CANCELLED
        assert protected.cancel_reason == "global_reminder_disabled"
        assert Message.query.filter_by(reminder_id=reminder.id).count() == 1


@pytest.mark.parametrize(
    ("path", "expected_reason"),
    [
        ("unsubscribe", "subscription_cancelled"),
        ("patch", "subscription_offset_not_future"),
    ],
)
def test_subscription_revocation_keeps_requeued_attempt_failed(
    app, engagement_fixture, path: str, expected_reason: str
) -> None:
    student, competition, _, node = engagement_fixture
    with app.app_context():
        failed_at = datetime.now(UTC) - timedelta(minutes=1)
        reminder = _current_pending_reminder(student, competition, node)
        reminder.attempt_count = 1
        reminder.failed_at = failed_at
        reminder.last_error_code = "message_persistence_unavailable"
        db.session.add(reminder)
        db.session.commit()

        if path == "unsubscribe":
            cancel_subscription(student, competition.id)
        else:
            update_subscription(student, competition.id, _payload(remind_days=30))

        revoked = db.session.get(Reminder, reminder.id)
        assert revoked.status == ReminderStatus.FAILED
        assert revoked.cancel_reason == expected_reason
        assert revoked.attempt_count == 1
        assert stored_datetime_as_utc(revoked.failed_at) == stored_datetime_as_utc(failed_at)
        assert revoked.last_error_code == "message_persistence_unavailable"
        assert revoked.next_attempt_at is None


def _current_pending_reminder(
    student: User,
    competition: Competition,
    node: CompetitionTimeNode,
) -> Reminder:
    return Reminder(
        id=60,
        user_id=student.id,
        competition_id=competition.id,
        time_node_snapshot_id=node.id,
        logical_node_key=node.logical_node_key,
        time_node_revision=node.node_revision,
        node_type=node.node_type,
        due_at=stored_datetime_as_utc(node.occurs_at) - timedelta(days=3),
        title="current pending",
        status=ReminderStatus.PENDING,
    )


@pytest.mark.parametrize(
    "reason",
    [
        "subscription_cancelled",
        "reminder_disabled",
        "node_type_removed",
        "subscription_offset_not_future",
    ],
)
def test_semantic_consent_change_restores_each_controlled_cancelled_plan(
    app, engagement_fixture, reason
) -> None:
    student, competition, subscription, node = engagement_fixture
    with app.app_context():
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="old",
            body="old body",
            status=ReminderStatus.CANCELLED,
            cancel_reason=reason,
        )
        db.session.add(reminder)
        db.session.commit()

        updated = update_subscription(student, competition.id, _payload(remind_days=2))
        restored = db.session.get(Reminder, reminder.id)
        assert updated.id == subscription.id
        assert restored.status == ReminderStatus.PENDING
        assert restored.cancel_reason is None
        assert restored.time_node_snapshot_id == node.id
        assert restored.due_at == node.occurs_at - timedelta(days=2)
        assert restored.title.endswith(": registration_deadline")
        assert (
            db.session.query(Reminder)
            .filter_by(
                user_id=student.id,
                competition_id=competition.id,
                logical_node_key=node.logical_node_key,
                time_node_revision=node.node_revision,
            )
            .count()
            == 1
        )


@pytest.mark.parametrize(
    "status,reason",
    [
        (ReminderStatus.SENT, "subscription_cancelled"),
        (ReminderStatus.FAILED, "subscription_cancelled"),
        (ReminderStatus.CANCELLED, "global_reminder_disabled"),
        (ReminderStatus.CANCELLED, "system_owned"),
    ],
)
def test_terminal_or_system_owned_plan_is_not_restored(
    app, engagement_fixture, status, reason
) -> None:
    student, competition, _, node = engagement_fixture
    with app.app_context():
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="terminal",
            status=status,
            cancel_reason=reason,
        )
        message = Message(
            id=70,
            user_id=student.id,
            reminder=reminder,
            competition_id=competition.id,
            message_type="reminder_due",
            idempotency_key="reminder_due:60",
            event_occurred_at=reminder.due_at,
            title_snapshot="Delivered evidence",
            body_snapshot=None,
            target_snapshot={
                "competition_id": competition.id,
                "competition_title": competition.title,
                "node_type": node.node_type,
                "node_occurs_at": node.occurs_at.isoformat(),
                "reason_summary": None,
            },
            retained_until=datetime.now(UTC) + timedelta(days=365),
        )
        db.session.add_all([reminder, message])
        db.session.commit()

        update_subscription(student, competition.id, _payload(remind_days=2))
        protected = db.session.get(Reminder, reminder.id)
        assert protected.status == status
        assert protected.cancel_reason == reason
        assert protected.title == "terminal"
        assert db.session.get(Message, message.id).title_snapshot == "Delivered evidence"


def test_post_resubscription_restores_subscription_cancelled_plan(app, engagement_fixture) -> None:
    student, competition, subscription, node = engagement_fixture
    with app.app_context():
        subscription.status = SubscriptionStatus.CANCELLED
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="cancelled",
            status=ReminderStatus.CANCELLED,
            cancel_reason="subscription_cancelled",
        )
        db.session.add(reminder)
        db.session.commit()

        mutation = subscribe_to_competition(student, competition.id, _payload(remind_days=2))
        assert mutation.created is False
        assert mutation.subscription.id == subscription.id
        assert db.session.get(Reminder, reminder.id).status == ReminderStatus.PENDING


@pytest.mark.parametrize(
    ("blocked_by", "expected_reason"),
    [
        ("subscription", "reminder_disabled"),
        ("global", "global_reminder_disabled"),
        ("past_due", "subscription_offset_not_future"),
        ("old_revision", "reminder_disabled"),
    ],
)
def test_controlled_cancelled_plan_stays_terminal_when_restoration_is_ineligible(
    app, engagement_fixture, blocked_by, expected_reason
) -> None:
    student, competition, subscription, node = engagement_fixture
    with app.app_context():
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="cancelled",
            status=ReminderStatus.CANCELLED,
            cancel_reason="reminder_disabled",
        )
        if blocked_by == "global":
            db.session.get(ReminderSetting, 50).enabled = False
        elif blocked_by == "past_due":
            db.session.get(CompetitionTimeNode, node.id).occurs_at = datetime.now(UTC) + timedelta(
                days=1
            )
        elif blocked_by == "old_revision":
            reminder.time_node_revision = 0
        db.session.add(reminder)
        db.session.commit()

        payload = _payload(remind_days=2)
        if blocked_by == "subscription":
            payload["reminder_enabled"] = False
        update_subscription(student, competition.id, payload)

        protected = db.session.get(Reminder, reminder.id)
        assert protected.status == ReminderStatus.CANCELLED
        assert protected.cancel_reason == expected_reason
        assert protected.id == reminder.id


def test_controlled_cancelled_plan_for_an_unselected_node_is_not_restored(
    app, engagement_fixture
) -> None:
    student, competition, _, node = engagement_fixture
    with app.app_context():
        current_competition = db.session.get(Competition, competition.id)
        unselected = CompetitionTimeNode(
            id=31,
            competition_id=current_competition.id,
            competition_revision_id=current_competition.published_revision_id,
            logical_node_key="submission-deadline",
            node_revision=1,
            node_type="submission_deadline",
            occurs_at=datetime.now(UTC) + timedelta(days=20),
        )
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=unselected.id,
            logical_node_key=unselected.logical_node_key,
            time_node_revision=unselected.node_revision,
            node_type=unselected.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="unselected",
            status=ReminderStatus.CANCELLED,
            cancel_reason="node_type_removed",
        )
        db.session.add_all([unselected, reminder])
        db.session.commit()

        update_subscription(student, competition.id, _payload(remind_days=2))
        protected = db.session.get(Reminder, reminder.id)
        assert protected.status == ReminderStatus.CANCELLED
        assert protected.cancel_reason == "node_type_removed"
        assert protected.time_node_snapshot_id == unselected.id


def test_semantic_patch_normalizes_existing_stored_order_without_renewing_consent(
    app, engagement_fixture
) -> None:
    student, competition, subscription, node = engagement_fixture
    with app.app_context():
        db.session.add(
            CompetitionTimeNode(
                id=31,
                competition_id=competition.id,
                competition_revision_id=competition.published_revision_id,
                logical_node_key="submission-deadline",
                node_revision=1,
                node_type="submission_deadline",
                occurs_at=datetime.now(UTC) + timedelta(days=20),
            )
        )
        subscription.node_types = ["submission_deadline", "registration_deadline"]
        subscription.reminder_confirmed_at = datetime(2026, 7, 1, tzinfo=UTC)
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="existing",
            status=ReminderStatus.PENDING,
        )
        db.session.add(reminder)
        db.session.commit()

        updated = update_subscription(
            student,
            competition.id,
            _payload(node_types=["submission_deadline", "registration_deadline"]),
        )

        assert updated.reminder_confirmed_at == datetime(2026, 7, 1)
        assert updated.node_types == ["registration_deadline", "submission_deadline"]
        assert db.session.get(Reminder, reminder.id).id == reminder.id
        assert db.session.get(Reminder, reminder.id).status == ReminderStatus.PENDING


def test_subscription_summary_canonicalizes_stored_node_types(app, engagement_fixture) -> None:
    _, _, subscription, _ = engagement_fixture
    with app.app_context():
        subscription.node_types = ["competition_start", "registration_deadline"]
        db.session.commit()

        assert subscription_summary(subscription)["node_types"] == [
            "registration_deadline",
            "competition_start",
        ]


def test_cancelling_subscription_for_missing_competition_rejects_without_mutation(
    app, engagement_fixture
) -> None:
    student, competition, subscription, _ = engagement_fixture
    with app.app_context():
        with pytest.raises(ServiceError, match="competition not found") as error:
            cancel_subscription(student, competition.id + 1)

        assert error.value.status_code == 404
        assert error.value.code == "not_found"
        persisted = db.session.get(Subscription, subscription.id)
        assert persisted.status == SubscriptionStatus.ACTIVE
        assert (
            db.session.query(Reminder)
            .filter_by(user_id=student.id, competition_id=competition.id)
            .count()
            == 0
        )


def test_initial_subscription_with_missing_reminder_settings_rolls_back(
    app, engagement_fixture
) -> None:
    student, competition, subscription, _ = engagement_fixture
    with app.app_context():
        student = db.session.get(User, student.id)
        competition = db.session.get(Competition, competition.id)
        subscription = db.session.get(Subscription, subscription.id)
        db.session.delete(subscription)
        db.session.delete(db.session.get(ReminderSetting, 50))
        db.session.commit()

        with pytest.raises(ServiceError, match="student-owned profile data is missing") as error:
            subscribe_to_competition(student, competition.id, _payload())

        assert error.value.status_code == 500
        assert error.value.code == "internal_server_error"
        assert (
            db.session.query(Subscription)
            .filter_by(user_id=student.id, competition_id=competition.id)
            .count()
            == 0
        )
        assert (
            db.session.query(Reminder)
            .filter_by(user_id=student.id, competition_id=competition.id)
            .count()
            == 0
        )


def test_resubscription_with_missing_reminder_settings_rolls_back(app, engagement_fixture) -> None:
    student, competition, subscription, node = engagement_fixture
    with app.app_context():
        student = db.session.get(User, student.id)
        competition = db.session.get(Competition, competition.id)
        subscription = db.session.get(Subscription, subscription.id)
        node = db.session.get(CompetitionTimeNode, node.id)
        subscription.status = SubscriptionStatus.CANCELLED
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="cancelled",
            status=ReminderStatus.CANCELLED,
            cancel_reason="subscription_cancelled",
        )
        db.session.add(reminder)
        db.session.delete(db.session.get(ReminderSetting, 50))
        db.session.commit()

        with pytest.raises(ServiceError, match="student-owned profile data is missing"):
            subscribe_to_competition(student, competition.id, _payload(remind_days=2))

        persisted = db.session.get(Subscription, subscription.id)
        preserved = db.session.get(Reminder, reminder.id)
        assert persisted.status == SubscriptionStatus.CANCELLED
        assert persisted.remind_days == 3
        assert preserved.status == ReminderStatus.CANCELLED
        assert preserved.cancel_reason == "subscription_cancelled"
        assert preserved.due_at == reminder.due_at


def test_semantic_subscription_patch_with_missing_reminder_settings_rolls_back(
    app, engagement_fixture
) -> None:
    student, competition, subscription, node = engagement_fixture
    with app.app_context():
        student = db.session.get(User, student.id)
        competition = db.session.get(Competition, competition.id)
        subscription = db.session.get(Subscription, subscription.id)
        node = db.session.get(CompetitionTimeNode, node.id)
        reminder = Reminder(
            id=60,
            user_id=student.id,
            competition_id=competition.id,
            time_node_snapshot_id=node.id,
            logical_node_key=node.logical_node_key,
            time_node_revision=node.node_revision,
            node_type=node.node_type,
            due_at=datetime.now(UTC) + timedelta(days=1),
            title="existing",
            status=ReminderStatus.PENDING,
        )
        db.session.add(reminder)
        db.session.delete(db.session.get(ReminderSetting, 50))
        db.session.commit()

        with pytest.raises(ServiceError, match="student-owned profile data is missing"):
            update_subscription(student, competition.id, _payload(remind_days=2))

        persisted = db.session.get(Subscription, subscription.id)
        preserved = db.session.get(Reminder, reminder.id)
        assert persisted.remind_days == 3
        assert persisted.node_types == ["registration_deadline"]
        assert preserved.status == ReminderStatus.PENDING
        assert preserved.due_at == reminder.due_at


def test_subscription_summary_rejects_missing_authoritative_reminder_settings(
    app, engagement_fixture
) -> None:
    _, _, subscription, _ = engagement_fixture
    with app.app_context():
        subscription = db.session.get(Subscription, subscription.id)
        db.session.delete(db.session.get(ReminderSetting, 50))
        db.session.commit()

        with pytest.raises(ServiceError, match="student-owned profile data is missing") as error:
            subscription_summary(subscription)

        assert error.value.status_code == 500
        assert error.value.code == "internal_server_error"


def test_reminder_reconciliation_with_missing_reminder_settings_rejects_before_planning(
    app, engagement_fixture
) -> None:
    student, competition, subscription, node = engagement_fixture
    with app.app_context():
        student = db.session.get(User, student.id)
        competition = db.session.get(Competition, competition.id)
        subscription = db.session.get(Subscription, subscription.id)
        node = db.session.get(CompetitionTimeNode, node.id)
        db.session.delete(db.session.get(ReminderSetting, 50))
        db.session.commit()

        with pytest.raises(ServiceError, match="student-owned profile data is missing"):
            _reconcile_subscription_reminders(
                subscription,
                competition,
                [node],
                datetime.now(UTC),
            )

        assert (
            db.session.query(Reminder)
            .filter_by(user_id=student.id, competition_id=competition.id)
            .count()
            == 0
        )
