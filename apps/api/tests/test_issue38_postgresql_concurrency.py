from __future__ import annotations

import os
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from flask_migrate import upgrade
from psycopg import connect, sql
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from test_public_competitions import seed_day1_competitions, sign_in_as, subscription_payload

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import Favorite, Reminder, ReminderSetting, Subscription, User
from competehub_api.models.enums import ReminderStatus, SubscriptionStatus, UserRole
from competehub_api.services.profiles import provision_student_owned_rows

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


@pytest.fixture()
def postgresql_database_uri():
    """A disposable real PostgreSQL database; never fall back to SQLite."""
    admin_dsn = os.getenv("POSTGRES_TEST_ADMIN_URL")
    if not admin_dsn:
        pytest.skip("POSTGRES_TEST_ADMIN_URL is required for PostgreSQL concurrency evidence")

    database_name = f"competehub_issue38_concurrency_{uuid.uuid4().hex}"
    with connect(admin_dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    database_url = (
        make_url(admin_dsn)
        .set(drivername="postgresql+psycopg", database=database_name)
        .render_as_string(hide_password=False)
    )
    try:
        yield database_url
    finally:
        with connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )


@pytest.fixture()
def postgresql_app(postgresql_database_uri):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "issue38-postgresql-concurrency",
            "SQLALCHEMY_DATABASE_URI": postgresql_database_uri,
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        upgrade(directory=MIGRATIONS_DIR)
        seed_day1_competitions()
    yield app
    with app.app_context():
        db.session.remove()


def _run_together(*operations: Callable[[], object]) -> list[object]:
    """Run independent request contexts together and surface every worker failure."""
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
        assert not thread.is_alive(), "concurrent request worker did not complete"
    assert failures == [None] * len(operations), failures
    return [result for result in results]


def _clients_for_same_student(app) -> tuple[int, object, object]:
    first = app.test_client()
    second = app.test_client()
    student_id = sign_in_as(first, app)
    with (
        first.session_transaction() as first_session,
        second.session_transaction() as second_session,
    ):
        for key, value in first_session.items():
            second_session[key] = value
    return student_id, first, second


def _barrier_after_absent_relation(monkeypatch, model: type[Favorite] | type[Subscription]) -> None:
    """Make both workers observe an absent relation before either can create it."""
    barrier = threading.Barrier(2)
    original_scalar = Session.scalar

    def scalar(session, statement, *args, **kwargs):
        result = original_scalar(session, statement, *args, **kwargs)
        descriptions = getattr(statement, "column_descriptions", ())
        if result is None and descriptions and descriptions[0].get("entity") is model:
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(Session, "scalar", scalar)


def test_postgresql_simultaneous_first_favorite_post_creates_one_row_and_recovers_loser(
    postgresql_app, monkeypatch
) -> None:
    student_id, first, second = _clients_for_same_student(postgresql_app)
    _barrier_after_absent_relation(monkeypatch, Favorite)

    responses = _run_together(
        lambda: first.post("/api/v1/competitions/101/favorite"),
        lambda: second.post("/api/v1/competitions/101/favorite"),
    )

    assert sorted(response.status_code for response in responses) == [200, 201]
    with postgresql_app.app_context():
        assert (
            db.session.query(Favorite).filter_by(user_id=student_id, competition_id=101).count()
            == 1
        )


def test_postgresql_simultaneous_first_subscription_post_preserves_winner_consent(
    postgresql_app, monkeypatch
) -> None:
    student_id, first, second = _clients_for_same_student(postgresql_app)
    _barrier_after_absent_relation(monkeypatch, Subscription)
    first_payload = subscription_payload(remind_days=1)
    second_payload = subscription_payload(reminder_enabled=False, remind_days=9)

    responses = _run_together(
        lambda: first.post("/api/v1/competitions/101/subscription", json=first_payload),
        lambda: second.post("/api/v1/competitions/101/subscription", json=second_payload),
    )

    assert sorted(response.status_code for response in responses) == [200, 201]
    with postgresql_app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        assert subscription.reminder_confirmed_at is not None
        assert (subscription.reminder_enabled, subscription.remind_days) in {
            (True, 1),
            (False, 9),
        }
        assert (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).count()
            == 1
        )


@pytest.mark.parametrize("initial_relation", ["absent", "cancelled"])
def test_postgresql_subscription_post_and_delete_serialize_without_duplicate_plans(
    postgresql_app, initial_relation
) -> None:
    student_id, first, second = _clients_for_same_student(postgresql_app)
    if initial_relation == "cancelled":
        created = first.post("/api/v1/competitions/101/subscription", json=subscription_payload())
        assert created.status_code == 201
        assert first.delete("/api/v1/competitions/101/subscription").status_code == 200

    responses = _run_together(
        lambda: first.post("/api/v1/competitions/101/subscription", json=subscription_payload()),
        lambda: second.delete("/api/v1/competitions/101/subscription"),
    )

    post_response, delete_response = responses
    assert delete_response.status_code == 200
    assert post_response.status_code == (201 if initial_relation == "absent" else 200)
    with postgresql_app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        reminders = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .order_by(Reminder.id)
            .all()
        )
        assert subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED}
        assert len(reminders) == 2
        assert len(
            {
                (reminder.logical_node_key, reminder.time_node_revision)
                for reminder in reminders
            }
        ) == 2
        if subscription.status == SubscriptionStatus.ACTIVE:
            assert all(reminder.status == ReminderStatus.PENDING for reminder in reminders)
        else:
            assert [(reminder.status, reminder.cancel_reason) for reminder in reminders] == [
                (ReminderStatus.CANCELLED, "subscription_cancelled"),
                (ReminderStatus.CANCELLED, "subscription_cancelled"),
            ]


def test_postgresql_subscription_patch_and_delete_serialize_without_partial_consent(
    postgresql_app,
) -> None:
    student_id, first, second = _clients_for_same_student(postgresql_app)
    created = first.post("/api/v1/competitions/101/subscription", json=subscription_payload())
    assert created.status_code == 201
    with postgresql_app.app_context():
        sent_reminder = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101, node_type="registration_deadline")
            .one()
        )
        sent_reminder.status = ReminderStatus.SENT
        sent_reminder.sent_at = datetime(2026, 8, 12, 16, 0, tzinfo=UTC)
        db.session.commit()
        sent_snapshot = (
            sent_reminder.id,
            sent_reminder.due_at,
            sent_reminder.title,
            sent_reminder.sent_at,
        )

    responses = _run_together(
        lambda: first.patch(
            "/api/v1/competitions/101/subscription", json=subscription_payload(remind_days=2)
        ),
        lambda: second.delete("/api/v1/competitions/101/subscription"),
    )

    patch_response, delete_response = responses
    assert delete_response.status_code == 200
    assert patch_response.status_code in {200, 409}
    if patch_response.status_code == 409:
        assert patch_response.get_json()["error"]["code"] == "engagement_unavailable"
    with postgresql_app.app_context():
        subscription = (
            db.session.query(Subscription).filter_by(user_id=student_id, competition_id=101).one()
        )
        reminders = (
            db.session.query(Reminder)
            .filter_by(user_id=student_id, competition_id=101)
            .order_by(Reminder.id)
            .all()
        )
        assert subscription.status == SubscriptionStatus.CANCELLED
        assert subscription.remind_days == (2 if patch_response.status_code == 200 else 3)
        assert len(reminders) == 2
        assert len(
            {
                (reminder.logical_node_key, reminder.time_node_revision)
                for reminder in reminders
            }
        ) == 2
        sent = next(reminder for reminder in reminders if reminder.id == sent_snapshot[0])
        assert (sent.id, sent.due_at, sent.title, sent.sent_at) == sent_snapshot
        pending = [reminder for reminder in reminders if reminder.id != sent.id]
        assert [(reminder.status, reminder.cancel_reason) for reminder in pending] == [
            (ReminderStatus.CANCELLED, "subscription_cancelled")
        ]


def test_postgresql_global_disable_locks_settings_then_pending_reminders_and_rolls_back(
    postgresql_app, monkeypatch
) -> None:
    first = postgresql_app.test_client()
    with postgresql_app.app_context():
        user = User(
            password_hash="not-used",
            display_name="Preference Student",
            role=UserRole.STUDENT,
        )
        db.session.add(user)
        db.session.flush()
        provision_student_owned_rows(user)
        db.session.flush()
        setting = db.session.query(ReminderSetting).filter_by(user_id=user.id).one()
        db.session.add_all(
            [
                Reminder(
                    user_id=user.id,
                    competition_id=101,
                    time_node_snapshot_id=201,
                    logical_node_key="registration",
                    time_node_revision=1,
                    node_type="registration_deadline",
                    due_at=datetime(2026, 8, 1, tzinfo=UTC),
                    title="one",
                    status=ReminderStatus.PENDING,
                ),
                Reminder(
                    user_id=user.id,
                    competition_id=101,
                    time_node_snapshot_id=202,
                    logical_node_key="submission",
                    time_node_revision=1,
                    node_type="submission_deadline",
                    due_at=datetime(2026, 8, 2, tzinfo=UTC),
                    title="two",
                    status=ReminderStatus.PENDING,
                ),
            ]
        )
        db.session.commit()
        user_id = user.id
        setting_id = setting.id
    with first.session_transaction() as browser_session:
        browser_session.update(
            user_id=user_id,
            session_version=1,
            issued_at=datetime.now(UTC).isoformat(),
            last_activity_at=datetime.now(UTC).isoformat(),
        )

    response = first.patch("/api/v1/me/preferences", json={"message_enabled": False})

    assert response.status_code == 200
    with postgresql_app.app_context():
        assert db.session.get(ReminderSetting, setting_id).enabled is False
        reminders = (
            db.session.query(Reminder).filter_by(user_id=user_id).order_by(Reminder.id).all()
        )
        assert [(row.status, row.cancel_reason) for row in reminders] == [
            (ReminderStatus.CANCELLED, "global_reminder_disabled"),
            (ReminderStatus.CANCELLED, "global_reminder_disabled"),
        ]
