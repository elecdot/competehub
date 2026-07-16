from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from itsdangerous import SignatureExpired, TimestampSigner

from competehub_api import create_app
from competehub_api.e2e_seed import E2E_ACTORS, SEEDED_E2E_ACTORS
from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    Favorite,
    Message,
    RecommendationRuleSet,
    Reminder,
    ReminderSetting,
    StudentProfile,
    Subscription,
    User,
    UserIdentity,
)
from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ReminderStatus,
    SubscriptionStatus,
    UserRole,
)
from competehub_api.services.profiles import DEFAULT_REMINDER_NODE_TYPES
from competehub_api.timezones import stored_datetime_as_utc


def test_e2e_seed_refuses_a_normal_application(app) -> None:
    result = app.test_cli_runner().invoke(args=["seed-e2e", "--reset"])

    assert result.exit_code != 0
    assert "requires the isolated E2E app factory" in result.output


def test_e2e_session_tolerates_a_one_second_clock_reversal(monkeypatch) -> None:
    app = create_app(
        {
            "TESTING": True,
            "E2E_TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    serializer = app.session_interface.get_signing_serializer(app)
    assert serializer is not None

    current_timestamp = [1_800_000_000]
    monkeypatch.setattr(
        TimestampSigner,
        "get_timestamp",
        lambda _signer: current_timestamp[0],
    )
    cookie = serializer.dumps({"user_id": 1001})

    current_timestamp[0] -= 1
    assert serializer.loads(cookie, max_age=60) == {"user_id": 1001}

    current_timestamp[0] -= 1
    with pytest.raises(SignatureExpired):
        serializer.loads(cookie, max_age=60)


def test_e2e_seed_rebuilds_the_expected_actor_set() -> None:
    app = create_app(
        {
            "TESTING": True,
            "E2E_TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )

    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-e2e", "--reset"])

    assert result.exit_code == 0
    assert "Provisioned 7 deterministic E2E actors." in result.output

    with app.app_context():
        db.session.add(
            User(
                id=9999,
                email="stray@example.edu",
                password_hash="not-used",
                display_name="Stray Actor",
            )
        )
        db.session.commit()

    second_result = runner.invoke(args=["seed-e2e", "--reset"])
    assert second_result.exit_code == 0

    with app.app_context():
        users = db.session.query(User).order_by(User.id).all()
        identities = db.session.query(UserIdentity).order_by(UserIdentity.user_id).all()
        profiles = db.session.query(StudentProfile).all()
        reminder_settings = db.session.query(ReminderSetting).all()

        expected_actors = sorted(SEEDED_E2E_ACTORS, key=lambda actor: actor.id)
        calendar_actors = [actor for actor in E2E_ACTORS if actor.id == 1007]
        assert len(calendar_actors) == 1
        assert calendar_actors[0].email == "calendar.student-day1@example.edu"
        assert [user.id for user in users] == [actor.id for actor in expected_actors]
        assert [user.email for user in users] == [actor.email for actor in expected_actors]
        assert [user.display_name for user in users] == [
            actor.display_name for actor in expected_actors
        ]
        assert [user.role for user in users] == [actor.role for actor in expected_actors]
        assert [user.status for user in users] == [actor.status for actor in expected_actors]
        assert [user.capabilities for user in users] == [
            list(actor.capabilities) for actor in expected_actors
        ]
        submitter = next(user for user in users if user.email == "admin.day1@example.edu")
        assert "recommendation_editor" in submitter.capabilities
        assert "recommendation_reviewer" in submitter.capabilities
        assert [identity.display_value for identity in identities] == [
            actor.email for actor in expected_actors
        ]
        assert [identity.verification_status for identity in identities] == [
            actor.verification_status for actor in expected_actors
        ]
        assert sorted(profile.user_id for profile in profiles) == sorted(
            actor.id for actor in SEEDED_E2E_ACTORS if actor.role == UserRole.STUDENT
        )
        assert sorted(setting.user_id for setting in reminder_settings) == sorted(
            actor.id for actor in SEEDED_E2E_ACTORS if actor.role == UserRole.STUDENT
        )
        assert all(setting.enabled is True for setting in reminder_settings)
        assert all(setting.default_remind_days == 3 for setting in reminder_settings)
        assert all(
            setting.node_types == DEFAULT_REMINDER_NODE_TYPES for setting in reminder_settings
        )
        series = db.session.get(CompetitionSeries, 2001)
        edition = db.session.get(Competition, 2001)
        revision = db.session.get(CompetitionRevision, 2001)
        historical_edition = db.session.get(Competition, 2004)
        historical_revision = db.session.get(CompetitionRevision, 2004)
        assert series.canonical_name == "Seeded University Innovation Challenge"
        assert edition.published_revision_id == revision.id
        assert revision.revision_status == CompetitionRevisionStatus.APPROVED
        assert revision.stages[0].stage_order == 1
        assert revision.stages[0].time_nodes[0].occurs_at is not None
        deadline = next(
            node
            for node in revision.stages[0].time_nodes
            if node.logical_node_key == "registration-deadline"
        )
        assert deadline.occurs_at is not None
        assert stored_datetime_as_utc(deadline.occurs_at) > datetime.now(UTC)
        assert revision.stages[0].time_nodes[0].starts_at is None
        assert revision.stages[0].time_nodes[0].due_at is None
        assert revision.official_url == "https://example.org/seeded-innovation-2025"
        assert historical_edition.status == CompetitionStatus.ARCHIVED
        assert historical_edition.lifecycle_reason == (
            "Official archive notice retained for student reference."
        )
        assert historical_edition.lifecycle_changed_at is not None
        assert historical_edition.published_revision_id == historical_revision.id
        assert [link.tag.name for link in revision.tag_links] == ["人工智能"]
        recommendation_rule_set = db.session.query(RecommendationRuleSet).one()
        assert recommendation_rule_set.version == 1
        assert recommendation_rule_set.status.value == "active"
        offline = db.session.get(Competition, 2002)
        unpublished = db.session.get(Competition, 2003)
        assert offline.status == CompetitionStatus.OFFLINE
        assert unpublished.status == CompetitionStatus.UNPUBLISHED
        offline_favorite = db.session.get(Favorite, 2002)
        unpublished_subscription = db.session.get(Subscription, 2003)
        historical_subscription = db.session.get(Subscription, 2004)
        message_subscription = db.session.get(Subscription, 2001)
        calendar_edition = db.session.get(Competition, 2005)
        calendar_revision = db.session.get(CompetitionRevision, 2005)
        legacy_calendar_revision = db.session.get(CompetitionRevision, 2105)
        calendar_subscription = db.session.get(Subscription, 2005)
        offline_calendar_subscription = db.session.get(Subscription, 2006)
        sent_reminder = db.session.get(Reminder, 3001)
        assert [
            subscription.id for subscription in Subscription.query.order_by(Subscription.id)
        ] == [
            2001,
            2003,
            2004,
            2005,
            2006,
        ]
        assert offline_favorite.user_id == E2E_ACTORS[0].id
        assert offline_favorite.is_active is True
        assert unpublished_subscription.user_id == E2E_ACTORS[0].id
        assert unpublished_subscription.status == SubscriptionStatus.ACTIVE
        assert historical_subscription.user_id == E2E_ACTORS[0].id
        assert historical_subscription.status == SubscriptionStatus.ACTIVE
        favorite_only_subscription = (
            db.session.query(Subscription)
            .filter_by(user_id=1001, competition_id=2002)
            .one_or_none()
        )
        assert favorite_only_subscription is None
        assert calendar_edition.published_revision_id == calendar_revision.id
        assert calendar_revision.revision_number == 2
        assert calendar_revision.revision_status == CompetitionRevisionStatus.APPROVED
        assert legacy_calendar_revision.revision_number == 1
        assert legacy_calendar_revision.revision_status == CompetitionRevisionStatus.APPROVED
        assert legacy_calendar_revision.title == "Legacy Calendar Challenge Revision 2026"
        assert [stage.id for stage in legacy_calendar_revision.stages] == [2511]
        assert [
            node.id for stage in legacy_calendar_revision.stages for node in stage.time_nodes
        ] == [2511]
        assert legacy_calendar_revision.stages[0].time_nodes[0].description == (
            "Legacy revision deadline that must not render"
        )
        assert [stage.id for stage in calendar_revision.stages] == [2501, 2502, 2503, 2504]
        assert [node.id for stage in calendar_revision.stages for node in stage.time_nodes] == [
            2501,
            2502,
            2503,
            2504,
        ]
        assert all(
            node.revision is calendar_revision
            for stage in calendar_revision.stages
            for node in stage.time_nodes
        )
        assert all(
            node.revision is legacy_calendar_revision
            for stage in legacy_calendar_revision.stages
            for node in stage.time_nodes
        )
        assert all(stage.id == stage.time_nodes[0].id for stage in calendar_revision.stages)
        assert all(
            stored_datetime_as_utc(node.occurs_at).date().isoformat() == "2026-07-16"
            for stage in calendar_revision.stages
            for node in stage.time_nodes
        )
        assert calendar_subscription.user_id == 1007
        assert calendar_subscription.status == SubscriptionStatus.ACTIVE
        assert calendar_subscription.reminder_enabled is False
        assert calendar_subscription.node_types == [
            "registration_deadline",
            "submission_deadline",
            "competition_start",
        ]
        assert offline_calendar_subscription.user_id == 1007
        assert offline_calendar_subscription.competition_id == offline.id
        assert offline_calendar_subscription.status == SubscriptionStatus.ACTIVE
        assert offline_calendar_subscription.reminder_enabled is False
        offline_revision = db.session.get(CompetitionRevision, 2002)
        assert offline_revision is not None
        assert [stage.id for stage in offline_revision.stages] == [2601]
        assert offline_revision.stages[0].time_nodes[0].id == 2601
        offline_node_occurs_at = stored_datetime_as_utc(
            offline_revision.stages[0].time_nodes[0].occurs_at
        )
        assert offline_node_occurs_at == datetime(2026, 7, 10, 1, 0, tzinfo=UTC)
        assert message_subscription.user_id == E2E_ACTORS[0].id
        assert message_subscription.competition_id == 2001
        assert message_subscription.status == SubscriptionStatus.CANCELLED
        assert sent_reminder.user_id == E2E_ACTORS[0].id
        assert sent_reminder.competition_id == 2001
        assert sent_reminder.status == ReminderStatus.SENT
        assert sent_reminder.attempt_count == 1
        assert sent_reminder.time_node_snapshot_id == 2001
        assert sent_reminder.logical_node_key == "registration-deadline"
        assert sent_reminder.time_node_revision == 1
        assert sent_reminder.node_type == "registration_deadline"
        assert stored_datetime_as_utc(sent_reminder.due_at) == (
            stored_datetime_as_utc(deadline.occurs_at)
            - timedelta(days=message_subscription.remind_days)
        )
        messages = Message.query.filter_by(user_id=1001).order_by(Message.created_at.desc()).all()
        assert [message.id for message in messages] == [3003, 3002, 3001]
        assert [message.is_read for message in messages] == [False, True, False]
        assert [message.message_type for message in messages] == [
            "competition_offline",
            "competition_time_changed",
            "reminder_due",
        ]
        assert messages[0].competition_id == 2002
        assert messages[1].competition_id == 2001
        assert messages[2].competition_id == 2001
        assert messages[2].reminder_id == sent_reminder.id
        assert stored_datetime_as_utc(messages[2].event_occurred_at) == (
            stored_datetime_as_utc(sent_reminder.due_at)
        )
        assert stored_datetime_as_utc(messages[2].created_at) == (
            stored_datetime_as_utc(sent_reminder.sent_at)
        )
        assert stored_datetime_as_utc(messages[2].created_at) > (
            stored_datetime_as_utc(sent_reminder.due_at)
        )
        assert all(
            (message.retained_until - message.created_at).days == 365 for message in messages
        )

    login_response = app.test_client().post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identifier": E2E_ACTORS[0].email,
            "password": E2E_ACTORS[0].password,
        },
    )

    assert login_response.status_code == 200


def test_e2e_seed_requires_an_explicit_reset() -> None:
    app = create_app(
        {
            "TESTING": True,
            "E2E_TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )

    result = app.test_cli_runner().invoke(args=["seed-e2e"])

    assert result.exit_code != 0
    assert "requires --reset" in result.output
