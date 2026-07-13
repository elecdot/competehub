from __future__ import annotations

from competehub_api import create_app
from competehub_api.e2e_seed import E2E_ACTORS, SEEDED_E2E_ACTORS
from competehub_api.extensions import db
from competehub_api.models import (
    Competition,
    CompetitionRevision,
    CompetitionSeries,
    ReminderSetting,
    StudentProfile,
    User,
    UserIdentity,
)
from competehub_api.models.enums import CompetitionRevisionStatus, UserRole
from competehub_api.services.profiles import DEFAULT_REMINDER_NODE_TYPES


def test_e2e_seed_refuses_a_normal_application(app) -> None:
    result = app.test_cli_runner().invoke(args=["seed-e2e", "--reset"])

    assert result.exit_code != 0
    assert "requires the isolated E2E app factory" in result.output


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
    assert "Provisioned 5 deterministic E2E actors." in result.output

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
        assert series.canonical_name == "Seeded University Innovation Challenge"
        assert edition.published_revision_id == revision.id
        assert revision.revision_status == CompetitionRevisionStatus.APPROVED
        assert revision.stages[0].stage_order == 1
        assert revision.stages[0].time_nodes[0].occurs_at is not None
        assert revision.stages[0].time_nodes[0].starts_at is None
        assert revision.stages[0].time_nodes[0].due_at is None

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
