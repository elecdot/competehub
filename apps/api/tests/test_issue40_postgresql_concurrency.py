from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from flask_migrate import upgrade
from test_competition_revisions import (
    create_published_edition,
    create_user,
    login,
)
from test_public_competitions import subscription_payload
from test_reminder_delivery import _seed_due_reminder

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import (
    AuditLog,
    Competition,
    CompetitionRevision,
    CompetitionTimeNode,
    Message,
    Reminder,
    ReminderSetting,
    ReviewRecord,
    Subscription,
    User,
)
from competehub_api.models.enums import ReminderStatus, UserRole
from competehub_api.repositories import engagement as engagement_repository
from competehub_api.services import competition_revisions as competition_revision_service
from competehub_api.services.notifications import create_competition_event_message
from competehub_api.services.profiles import provision_student_owned_rows
from competehub_api.services.reminder_delivery import (
    dispatch_due_reminders,
    requeue_failed_reminders,
)
from competehub_api.timezones import stored_datetime_as_utc

MIGRATIONS_DIR = "apps/api/migrations"


@pytest.fixture()
def postgresql_app(postgresql_database_uri):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "issue40-postgresql-concurrency",
            "SQLALCHEMY_DATABASE_URI": postgresql_database_uri,
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        upgrade(directory=MIGRATIONS_DIR)
    yield app
    with app.app_context():
        db.session.remove()


def _run_together(*operations: Callable[[], object]) -> list[object]:
    """Run independent transactions together and fail on hangs or worker errors."""
    start = threading.Barrier(len(operations))
    results: list[object | None] = [None] * len(operations)
    failures: list[BaseException | None] = [None] * len(operations)

    def worker(index: int, operation: Callable[[], object]) -> None:
        try:
            start.wait(timeout=10)
            results[index] = operation()
        except BaseException as error:  # surfaced in the test thread below
            failures[index] = error

    threads = [
        threading.Thread(target=worker, args=(index, operation))
        for index, operation in enumerate(operations)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
        assert not thread.is_alive(), "concurrent transaction worker did not complete"
    assert failures == [None] * len(operations), failures
    return [result for result in results]


def _authenticated_clients(app, user_id: int):
    clients = (app.test_client(), app.test_client())
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        session_version = user.session_version
    issued_at = datetime.now(UTC).isoformat()
    for client in clients:
        with client.session_transaction() as browser_session:
            browser_session.update(
                user_id=user_id,
                session_version=session_version,
                issued_at=issued_at,
                last_activity_at=issued_at,
            )
    return clients


def _dispatch_in_context(app, now: datetime) -> dict[str, int]:
    with app.app_context():
        return dispatch_due_reminders(now=now, limit=1)


def _requeue_in_context(app, now: datetime) -> dict[str, int]:
    with app.app_context():
        return requeue_failed_reminders(now=now, limit=1)


def _assert_leaf_dispatch_serial_outcome(reminder_id: int, stopped_reason: str) -> None:
    reminder = db.session.get(Reminder, reminder_id)
    messages = Message.query.filter_by(reminder_id=reminder_id).all()
    assert reminder is not None
    assert len(messages) <= 1
    assert reminder.failed_at is None
    assert reminder.last_error_code is None
    assert reminder.next_attempt_at is None
    if reminder.status == ReminderStatus.SENT:
        assert reminder.attempt_count == 1
        assert reminder.sent_at is not None
        assert reminder.cancel_reason is None
        assert len(messages) == 1
        assert messages[0].message_type == "reminder_due"
        return
    assert reminder.status == ReminderStatus.CANCELLED
    assert reminder.attempt_count == 0
    assert reminder.sent_at is None
    assert reminder.cancel_reason == stopped_reason
    assert messages == []


def test_postgresql_two_dispatch_workers_send_one_message_for_one_due_reminder(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder_id = _seed_due_reminder(now).id

    results = _run_together(
        lambda: _dispatch_in_context(postgresql_app, now),
        lambda: _dispatch_in_context(postgresql_app, now),
    )

    assert sorted(result["dispatched"] for result in results) == [0, 1]
    assert all(result["cancelled"] == 0 and result["failed"] == 0 for result in results)
    with postgresql_app.app_context():
        reminder = db.session.get(Reminder, reminder_id)
        assert reminder is not None
        assert reminder.status == ReminderStatus.SENT
        assert reminder.attempt_count == 1
        messages = Message.query.filter_by(reminder_id=reminder_id).all()
        assert len(messages) == 1
        assert messages[0].idempotency_key == f"reminder_due:{reminder_id}"


def test_postgresql_global_enable_and_subscription_patch_keep_one_current_plan(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    original_due_at = now + timedelta(days=1)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now, due_at=original_due_at)
        student_id = reminder.user_id
        reminder_id = reminder.id
        competition_id = reminder.competition_id
    enable_client, subscription_client = _authenticated_clients(postgresql_app, student_id)
    disabled = enable_client.patch("/api/v1/me/preferences", json={"message_enabled": False})
    assert disabled.status_code == 200

    responses = _run_together(
        lambda: enable_client.patch("/api/v1/me/preferences", json={"message_enabled": True}),
        lambda: subscription_client.patch(
            f"/api/v1/competitions/{competition_id}/subscription",
            json=subscription_payload(
                remind_days=2,
                node_types=["registration_deadline"],
            ),
        ),
    )

    assert [response.status_code for response in responses] == [200, 200]
    with postgresql_app.app_context():
        setting = ReminderSetting.query.filter_by(user_id=student_id).one()
        subscription = Subscription.query.filter_by(
            user_id=student_id, competition_id=competition_id
        ).one()
        reminders = Reminder.query.filter_by(
            user_id=student_id, competition_id=competition_id
        ).all()
        assert setting.enabled is True
        assert subscription.remind_days == 2
        assert len(reminders) == 1
        assert reminders[0].id == reminder_id
        assert reminders[0].status == ReminderStatus.PENDING
        assert reminders[0].cancel_reason is None
        assert stored_datetime_as_utc(reminders[0].due_at) == original_due_at + timedelta(days=1)


def test_postgresql_global_enable_and_subscription_cancel_leave_no_active_plan(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now, due_at=now + timedelta(days=1))
        student_id = reminder.user_id
        reminder_id = reminder.id
        competition_id = reminder.competition_id
    enable_client, cancel_client = _authenticated_clients(postgresql_app, student_id)
    disabled = enable_client.patch("/api/v1/me/preferences", json={"message_enabled": False})
    assert disabled.status_code == 200

    responses = _run_together(
        lambda: enable_client.patch("/api/v1/me/preferences", json={"message_enabled": True}),
        lambda: cancel_client.delete(f"/api/v1/competitions/{competition_id}/subscription"),
    )

    assert [response.status_code for response in responses] == [200, 200]
    with postgresql_app.app_context():
        setting = ReminderSetting.query.filter_by(user_id=student_id).one()
        subscription = Subscription.query.filter_by(
            user_id=student_id, competition_id=competition_id
        ).one()
        reminders = Reminder.query.filter_by(
            user_id=student_id, competition_id=competition_id
        ).all()
        assert setting.enabled is True
        assert subscription.status.value == "cancelled"
        assert len(reminders) == 1
        assert reminders[0].id == reminder_id
        assert reminders[0].status == ReminderStatus.CANCELLED
        assert reminders[0].cancel_reason == "subscription_cancelled"
        assert Message.query.filter_by(reminder_id=reminder_id).count() == 0


def test_postgresql_global_enable_and_resub_restore_one_current_plan(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    due_at = now + timedelta(days=1)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now, due_at=due_at)
        student_id = reminder.user_id
        reminder_id = reminder.id
        competition_id = reminder.competition_id
    enable_client, resub_client = _authenticated_clients(postgresql_app, student_id)
    disabled = enable_client.patch("/api/v1/me/preferences", json={"message_enabled": False})
    cancelled = enable_client.delete(f"/api/v1/competitions/{competition_id}/subscription")
    assert [disabled.status_code, cancelled.status_code] == [200, 200]
    with postgresql_app.app_context():
        cancelled_plan = db.session.get(Reminder, reminder_id)
        assert cancelled_plan is not None
        assert cancelled_plan.cancel_reason == "subscription_cancelled"

    responses = _run_together(
        lambda: enable_client.patch("/api/v1/me/preferences", json={"message_enabled": True}),
        lambda: resub_client.post(
            f"/api/v1/competitions/{competition_id}/subscription",
            json=subscription_payload(node_types=["registration_deadline"]),
        ),
    )

    assert [response.status_code for response in responses] == [200, 200]
    with postgresql_app.app_context():
        setting = ReminderSetting.query.filter_by(user_id=student_id).one()
        subscription = Subscription.query.filter_by(
            user_id=student_id, competition_id=competition_id
        ).one()
        reminders = Reminder.query.filter_by(
            user_id=student_id, competition_id=competition_id
        ).all()
        assert setting.enabled is True
        assert subscription.status.value == "active"
        assert len(reminders) == 1
        assert reminders[0].id == reminder_id
        assert reminders[0].status == ReminderStatus.PENDING
        assert reminders[0].cancel_reason is None
        assert stored_datetime_as_utc(reminders[0].due_at) == due_at


def test_postgresql_dispatch_and_global_disable_end_in_a_valid_serial_state(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now)
        student_id = reminder.user_id
        reminder_id = reminder.id
    disable_client, _ = _authenticated_clients(postgresql_app, student_id)

    dispatch_result, disable_response = _run_together(
        lambda: _dispatch_in_context(postgresql_app, now),
        lambda: disable_client.patch("/api/v1/me/preferences", json={"message_enabled": False}),
    )

    assert disable_response.status_code == 200
    with postgresql_app.app_context():
        setting = ReminderSetting.query.filter_by(user_id=student_id).one()
        reminder = db.session.get(Reminder, reminder_id)
        messages = Message.query.filter_by(reminder_id=reminder_id).all()
        assert setting.enabled is False
        assert reminder is not None
        assert len(messages) <= 1
        if reminder.status == ReminderStatus.SENT:
            assert dispatch_result == {"dispatched": 1, "cancelled": 0, "failed": 0}
            assert reminder.attempt_count == 1
            assert len(messages) == 1
        else:
            assert reminder.status == ReminderStatus.CANCELLED
            assert reminder.cancel_reason == "global_reminder_disabled"
            assert dispatch_result == {"dispatched": 0, "cancelled": 0, "failed": 0}
            assert reminder.attempt_count == 0
            assert messages == []


def test_postgresql_leaf_dispatch_and_unsubscribe_have_one_valid_serial_outcome(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now)
        student_id = reminder.user_id
        reminder_id = reminder.id
        competition_id = reminder.competition_id
    unsubscribe_client, _ = _authenticated_clients(postgresql_app, student_id)

    _, unsubscribe_response = _run_together(
        lambda: _dispatch_in_context(postgresql_app, now),
        lambda: unsubscribe_client.delete(f"/api/v1/competitions/{competition_id}/subscription"),
    )

    assert unsubscribe_response.status_code == 200
    with postgresql_app.app_context():
        subscription = Subscription.query.filter_by(
            user_id=student_id, competition_id=competition_id
        ).one()
        assert subscription.status.value == "cancelled"
        _assert_leaf_dispatch_serial_outcome(reminder_id, "subscription_cancelled")


def test_postgresql_leaf_dispatch_and_offline_have_one_valid_serial_outcome(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now)
        competition = db.session.get(Competition, reminder.competition_id)
        assert competition is not None
        publisher = db.session.get(User, competition.created_by_id)
        assert publisher is not None
        publisher.capabilities = ["competition_maintainer"]
        db.session.commit()
        reminder_id = reminder.id
        student_id = reminder.user_id
        competition_id = reminder.competition_id
        publisher_id = publisher.id
    maintainer_client, _ = _authenticated_clients(postgresql_app, publisher_id)

    _, offline_response = _run_together(
        lambda: _dispatch_in_context(postgresql_app, now),
        lambda: maintainer_client.patch(
            f"/api/v1/admin/competitions/{competition_id}/status",
            json={
                "status": "offline",
                "reason": "Official source integrity requires immediate withdrawal.",
            },
        ),
    )

    assert offline_response.status_code == 200
    with postgresql_app.app_context():
        competition = db.session.get(Competition, competition_id)
        assert competition is not None and competition.status.value == "offline"
        _assert_leaf_dispatch_serial_outcome(reminder_id, "competition_offline")
        assert (
            Message.query.filter_by(
                user_id=student_id,
                competition_id=competition_id,
                message_type="competition_offline",
            ).count()
            == 1
        )


def test_postgresql_global_disable_and_offline_serialize_on_competition_parent(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        failed = _seed_due_reminder(now, due_at=now + timedelta(days=1))
        failed.status = ReminderStatus.FAILED
        failed.attempt_count = 1
        failed.failed_at = now
        failed.last_error_code = "message_persistence_unavailable"
        failed.next_attempt_at = now + timedelta(minutes=1)
        competition = db.session.get(Competition, failed.competition_id)
        assert competition is not None
        publisher = db.session.get(User, competition.created_by_id)
        assert publisher is not None
        publisher.capabilities = ["competition_maintainer"]
        revision = db.session.get(CompetitionRevision, competition.published_revision_id)
        assert revision is not None
        second_node = CompetitionTimeNode(
            id=605,
            competition=competition,
            revision=revision,
            logical_node_key="submission-deadline",
            node_revision=1,
            node_type="submission_deadline",
            occurs_at=now + timedelta(days=5),
            prominence="primary",
        )
        pending = Reminder(
            id=608,
            user_id=failed.user_id,
            competition_id=failed.competition_id,
            time_node_snapshot_id=second_node.id,
            logical_node_key=second_node.logical_node_key,
            time_node_revision=second_node.node_revision,
            node_type=second_node.node_type,
            due_at=now + timedelta(days=2),
            title="Submission closes soon",
            status=ReminderStatus.PENDING,
        )
        db.session.add(second_node)
        db.session.flush()
        db.session.add(pending)
        db.session.commit()
        failed_id = failed.id
        pending_id = pending.id
        student_id = failed.user_id
        competition_id = failed.competition_id
        publisher_id = publisher.id
        assert failed_id < pending_id

    student_client, _ = _authenticated_clients(postgresql_app, student_id)
    maintainer_client, _ = _authenticated_clients(postgresql_app, publisher_id)

    disable_response, offline_response = _run_together(
        lambda: student_client.patch("/api/v1/me/preferences", json={"message_enabled": False}),
        lambda: maintainer_client.patch(
            f"/api/v1/admin/competitions/{competition_id}/status",
            json={
                "status": "offline",
                "reason": "Official source integrity requires immediate withdrawal.",
            },
        ),
    )

    assert [disable_response.status_code, offline_response.status_code] == [200, 200]
    with postgresql_app.app_context():
        setting = ReminderSetting.query.filter_by(user_id=student_id).one()
        competition = db.session.get(Competition, competition_id)
        failed = db.session.get(Reminder, failed_id)
        pending = db.session.get(Reminder, pending_id)
        assert setting.enabled is False
        assert competition is not None and competition.status.value == "offline"
        assert failed is not None and pending is not None
        assert failed.status == ReminderStatus.FAILED
        assert failed.next_attempt_at is None
        assert pending.status == ReminderStatus.CANCELLED
        assert {failed.cancel_reason, pending.cancel_reason} in (
            {"competition_offline"},
            {"global_reminder_disabled", "competition_offline"},
        )
        assert (
            Reminder.query.filter_by(
                user_id=student_id,
                competition_id=competition_id,
                status=ReminderStatus.PENDING,
            ).count()
            == 0
        )
        assert (
            Message.query.filter_by(
                user_id=student_id,
                competition_id=competition_id,
                message_type="competition_offline",
            ).count()
            == 1
        )


def test_postgresql_requeue_and_offset_revocation_never_send_the_failed_plan(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now)
        reminder.status = ReminderStatus.FAILED
        reminder.attempt_count = 1
        reminder.failed_at = now
        reminder.last_error_code = "message_persistence_unavailable"
        reminder.next_attempt_at = now
        db.session.commit()
        reminder_id = reminder.id
        student_id = reminder.user_id
        competition_id = reminder.competition_id
    subscription_client, _ = _authenticated_clients(postgresql_app, student_id)

    requeue_result, patch_response = _run_together(
        lambda: _requeue_in_context(postgresql_app, now),
        lambda: subscription_client.patch(
            f"/api/v1/competitions/{competition_id}/subscription",
            json=subscription_payload(
                remind_days=2,
                node_types=["registration_deadline"],
            ),
        ),
    )

    assert patch_response.status_code == 200
    assert requeue_result in (
        {"requeued": 0, "suppressed": 0},
        {"requeued": 1, "suppressed": 0},
    )
    with postgresql_app.app_context():
        reminder = db.session.get(Reminder, reminder_id)
        assert reminder is not None
        assert reminder.status == ReminderStatus.FAILED
        assert reminder.next_attempt_at is None
        assert reminder.cancel_reason == "subscription_offset_not_future"
        assert reminder.attempt_count == 1
        assert reminder.last_error_code == "message_persistence_unavailable"
        assert reminder.failed_at is not None
        assert Message.query.filter_by(reminder_id=reminder_id).count() == 0

        later = dispatch_due_reminders(now=now + timedelta(days=1, seconds=1))
        assert later == {"dispatched": 0, "cancelled": 0, "failed": 0}
        assert db.session.get(Reminder, reminder_id).status != ReminderStatus.SENT
        assert Message.query.filter_by(reminder_id=reminder_id).count() == 0


def test_postgresql_concurrent_reads_return_linearizable_unread_counts(postgresql_app) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now, due_at=now + timedelta(days=1))
        competition = db.session.get(Competition, reminder.competition_id)
        assert competition is not None
        first = create_competition_event_message(
            user_id=reminder.user_id,
            competition=competition,
            message_type="competition_time_changed",
            idempotency_key="issue40:concurrent-read:first",
            event_occurred_at=now,
            title_snapshot="First schedule change",
            body_snapshot=None,
            reason_summary="First change.",
        )
        second = create_competition_event_message(
            user_id=reminder.user_id,
            competition=competition,
            message_type="competition_time_changed",
            idempotency_key="issue40:concurrent-read:second",
            event_occurred_at=now,
            title_snapshot="Second schedule change",
            body_snapshot=None,
            reason_summary="Second change.",
        )
        db.session.commit()
        student_id = reminder.user_id
        message_ids = (first.id, second.id)

    first_client, second_client = _authenticated_clients(postgresql_app, student_id)
    responses = _run_together(
        lambda: first_client.post(f"/api/v1/me/messages/{message_ids[0]}/read"),
        lambda: second_client.post(f"/api/v1/me/messages/{message_ids[1]}/read"),
    )

    assert [response.status_code for response in responses] == [200, 200]
    assert sorted(response.get_json()["data"]["unread_count"] for response in responses) == [
        0,
        1,
    ]
    with postgresql_app.app_context():
        messages = Message.query.filter(Message.id.in_(message_ids)).order_by(Message.id).all()
        assert len(messages) == 2
        assert all(message.is_read for message in messages)
        assert all(message.read_at is not None for message in messages)


def test_postgresql_duplicate_event_race_preserves_both_outer_transactions(
    postgresql_app, monkeypatch
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with postgresql_app.app_context():
        reminder = _seed_due_reminder(now, due_at=now + timedelta(days=1))
        student_id = reminder.user_id
        competition_id = reminder.competition_id

    absent_read = threading.Barrier(2)
    worker_state = threading.local()
    original_get = engagement_repository.get_message_by_idempotency

    def get_after_both_observed_absent(user_id: int, idempotency_key: str):
        message = original_get(user_id, idempotency_key)
        if message is None and not getattr(worker_state, "waited", False):
            worker_state.waited = True
            absent_read.wait(timeout=10)
        return message

    monkeypatch.setattr(
        engagement_repository,
        "get_message_by_idempotency",
        get_after_both_observed_absent,
    )
    idempotency_key = "competition:503:revision:1:time_changed"

    def create_event_with_sentinel(label: str) -> int:
        with postgresql_app.app_context():
            competition = db.session.get(Competition, competition_id)
            assert competition is not None
            db.session.add(
                AuditLog(
                    actor_id=student_id,
                    action=f"issue40.concurrent.{label}",
                    target_type="competition",
                    target_id=competition_id,
                    result="success",
                    detail={"sentinel": label},
                )
            )
            db.session.flush()
            message = create_competition_event_message(
                user_id=student_id,
                competition=competition,
                message_type="competition_time_changed",
                idempotency_key=idempotency_key,
                event_occurred_at=now,
                title_snapshot="Schedule changed",
                body_snapshot="Review the updated timeline.",
                reason_summary="Timeline changed.",
            )
            message_id = message.id
            db.session.commit()
            return message_id

    message_ids = _run_together(
        lambda: create_event_with_sentinel("first"),
        lambda: create_event_with_sentinel("second"),
    )

    assert message_ids[0] == message_ids[1]
    with postgresql_app.app_context():
        messages = Message.query.filter_by(
            user_id=student_id, idempotency_key=idempotency_key
        ).all()
        sentinels = AuditLog.query.filter(
            AuditLog.action.in_(["issue40.concurrent.first", "issue40.concurrent.second"])
        ).all()
        assert len(messages) == 1
        assert len(sentinels) == 2
        assert {row.detail["sentinel"] for row in sentinels} == {"first", "second"}


def test_postgresql_leaf_dispatch_and_revision_approval_have_one_valid_serial_outcome(
    postgresql_app,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    dispatch_at = now + timedelta(minutes=5)
    editor = postgresql_app.test_client()
    reviewer = postgresql_app.test_client()
    student = postgresql_app.test_client()
    with postgresql_app.app_context():
        editor_id = create_user(
            701,
            UserRole.ADMIN,
            "issue40-dispatch-revision-editor@example.edu",
            ["competition_editor"],
        )
        reviewer_id = create_user(
            702,
            UserRole.ADMIN,
            "issue40-dispatch-revision-reviewer@example.edu",
            ["competition_reviewer"],
        )
        student_id = create_user(
            703,
            UserRole.STUDENT,
            "issue40-dispatch-revision-student@example.edu",
        )
        provision_student_owned_rows(db.session.get(User, student_id))
        db.session.commit()

    login(editor, editor_id)
    edition = create_published_edition(editor, editor_id, reviewer_id)
    edition_id = edition["id"]
    with postgresql_app.app_context():
        competition = db.session.get(Competition, edition_id)
        assert competition is not None and competition.published_revision is not None
        nodes = {node.logical_node_key: node for node in competition.published_revision.time_nodes}
        nodes["registration-open"].occurs_at = now + timedelta(days=10)
        nodes["registration-deadline"].occurs_at = dispatch_at + timedelta(days=30)
        db.session.commit()

    login(student, student_id)
    subscribed = student.post(
        f"/api/v1/competitions/{edition_id}/subscription",
        json=subscription_payload(
            remind_days=30,
            node_types=["registration_deadline"],
        ),
    )
    assert subscribed.status_code == 201
    with postgresql_app.app_context():
        old_reminder = Reminder.query.filter_by(
            user_id=student_id,
            competition_id=edition_id,
            logical_node_key="registration-deadline",
        ).one()
        assert stored_datetime_as_utc(old_reminder.due_at) == dispatch_at
        old_reminder_id = old_reminder.id

    successor = editor.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Move the registration deadline."},
    ).get_json()["data"]
    successor_id = successor["id"]
    stages = successor["stages"]
    deadline = next(
        node
        for stage in stages
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    deadline["occurs_at"] = (dispatch_at + timedelta(days=31)).isoformat()
    for stage in stages:
        stage.pop("id", None)
        for node in stage["time_nodes"]:
            node.pop("id", None)
            node.pop("node_revision", None)
    assert (
        editor.patch(
            f"/api/v1/admin/competition_revisions/{successor_id}",
            json={"stages": stages},
        ).status_code
        == 200
    )
    assert (
        editor.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )
    login(reviewer, reviewer_id)

    _, approval_response = _run_together(
        lambda: _dispatch_in_context(postgresql_app, dispatch_at),
        lambda: reviewer.post(
            f"/api/v1/admin/competition_revisions/{successor_id}/review",
            json={"action": "approve", "comment": "Updated deadline verified."},
        ),
    )

    assert approval_response.status_code == 200
    with postgresql_app.app_context():
        competition = db.session.get(Competition, edition_id)
        assert competition is not None
        assert competition.published_revision_id == successor_id
        _assert_leaf_dispatch_serial_outcome(
            old_reminder_id,
            "competition_revision_superseded",
        )
        current_plans = Reminder.query.filter_by(
            user_id=student_id,
            competition_id=edition_id,
            status=ReminderStatus.PENDING,
        ).all()
        assert len(current_plans) == 1
        assert current_plans[0].time_node_revision == 2
        assert stored_datetime_as_utc(current_plans[0].due_at) == dispatch_at + timedelta(days=1)


def test_postgresql_revision_approval_refreshes_setting_after_concurrent_global_disable(
    postgresql_app, monkeypatch
) -> None:
    editor = postgresql_app.test_client()
    reviewer = postgresql_app.test_client()
    student = postgresql_app.test_client()
    with postgresql_app.app_context():
        editor_id = create_user(
            601,
            UserRole.ADMIN,
            "issue40-stale-setting-editor@example.edu",
            ["competition_editor"],
        )
        reviewer_id = create_user(
            602,
            UserRole.ADMIN,
            "issue40-stale-setting-reviewer@example.edu",
            ["competition_reviewer"],
        )
        student_id = create_user(
            603,
            UserRole.STUDENT,
            "issue40-stale-setting-student@example.edu",
        )
        provision_student_owned_rows(db.session.get(User, student_id))
        db.session.commit()

    login(editor, editor_id)
    edition = create_published_edition(editor, editor_id, reviewer_id)
    edition_id = edition["id"]
    login(student, student_id)
    subscribed = student.post(
        f"/api/v1/competitions/{edition_id}/subscription",
        json=subscription_payload(node_types=["registration_deadline"]),
    )
    assert subscribed.status_code == 201

    successor = editor.post(
        f"/api/v1/admin/competitions/{edition_id}/revisions",
        json={"reason": "Move the registration deadline."},
    ).get_json()["data"]
    successor_id = successor["id"]
    stages = successor["stages"]
    deadline = next(
        node
        for stage in stages
        for node in stage["time_nodes"]
        if node["logical_node_key"] == "registration-deadline"
    )
    deadline["occurs_at"] = "2099-08-20T16:00:00Z"
    for stage in stages:
        stage.pop("id", None)
        for node in stage["time_nodes"]:
            node.pop("id", None)
            node.pop("node_revision", None)
    assert (
        editor.patch(
            f"/api/v1/admin/competition_revisions/{successor_id}",
            json={"stages": stages},
        ).status_code
        == 200
    )
    assert (
        editor.post(f"/api/v1/admin/competition_revisions/{successor_id}/submit_review").status_code
        == 200
    )
    login(reviewer, reviewer_id)

    global_parent_locked = threading.Event()
    continue_global_disable = threading.Event()
    approval_parent_lock_attempted = threading.Event()
    original_global_parent_lock = engagement_repository.list_user_reminder_competitions_for_update
    original_revision_parent_lock = competition_revision_service.get_competition_for_update

    def pause_after_global_parent_lock(user_id: int):
        competitions = original_global_parent_lock(user_id)
        global_parent_locked.set()
        assert continue_global_disable.wait(timeout=10)
        return competitions

    def observe_revision_parent_lock(competition_id: int):
        approval_parent_lock_attempted.set()
        return original_revision_parent_lock(competition_id)

    monkeypatch.setattr(
        engagement_repository,
        "list_user_reminder_competitions_for_update",
        pause_after_global_parent_lock,
    )
    monkeypatch.setattr(
        competition_revision_service,
        "get_competition_for_update",
        observe_revision_parent_lock,
    )
    disable_responses = []
    disable_failures = []
    approval_responses = []
    approval_failures = []

    def disable_globally() -> None:
        try:
            disable_responses.append(
                student.patch("/api/v1/me/preferences", json={"message_enabled": False})
            )
        except BaseException as error:  # surfaced in the test thread below
            disable_failures.append(error)

    def approve_successor() -> None:
        try:
            approval_responses.append(
                reviewer.post(
                    f"/api/v1/admin/competition_revisions/{successor_id}/review",
                    json={"action": "approve", "comment": "Updated deadline verified."},
                )
            )
        except BaseException as error:  # surfaced in the test thread below
            approval_failures.append(error)

    disable_thread = threading.Thread(target=disable_globally)
    disable_thread.start()
    assert global_parent_locked.wait(timeout=10)

    approval_thread = threading.Thread(target=approve_successor)
    approval_thread.start()
    assert approval_parent_lock_attempted.wait(timeout=10)
    continue_global_disable.set()
    disable_thread.join(timeout=15)
    approval_thread.join(timeout=15)
    assert not disable_thread.is_alive(), "global disable did not complete"
    assert not approval_thread.is_alive(), "revision approval did not complete"
    assert disable_failures == []
    assert approval_failures == []
    assert [response.status_code for response in disable_responses] == [200]
    assert [response.status_code for response in approval_responses] == [200]

    with postgresql_app.app_context():
        setting = ReminderSetting.query.filter_by(user_id=student_id).one()
        reminders = Reminder.query.filter_by(user_id=student_id, competition_id=edition_id).all()
        competition = db.session.get(Competition, edition_id)
        review = ReviewRecord.query.filter_by(
            target_type="competition_revision", target_id=successor_id
        ).one()
        assert setting.enabled is False
        assert competition is not None
        assert competition.published_revision_id == successor_id
        assert len(reminders) == 1
        assert all(reminder.status != ReminderStatus.PENDING for reminder in reminders)
        assert reminders[0].cancel_reason == "global_reminder_disabled"
        assert review.impact["pending_reminders_to_supersede"] == 0
        assert review.impact["future_reminders_to_create"] == 0
