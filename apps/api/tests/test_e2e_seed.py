from __future__ import annotations

from competehub_api import create_app
from competehub_api.e2e_seed import E2E_ACTORS
from competehub_api.extensions import db
from competehub_api.models import User
from competehub_api.models.enums import UserStatus


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
        }
    )

    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-e2e", "--reset"])

    assert result.exit_code == 0
    assert "Provisioned 3 deterministic E2E actors." in result.output

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

        assert [user.id for user in users] == [actor.id for actor in E2E_ACTORS]
        assert [user.email for user in users] == [actor.email for actor in E2E_ACTORS]
        assert [user.display_name for user in users] == [actor.display_name for actor in E2E_ACTORS]
        assert [user.role for user in users] == [actor.role for actor in E2E_ACTORS]
        assert all(user.status == UserStatus.ACTIVE for user in users)


def test_e2e_seed_requires_an_explicit_reset() -> None:
    app = create_app(
        {
            "TESTING": True,
            "E2E_TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    result = app.test_cli_runner().invoke(args=["seed-e2e"])

    assert result.exit_code != 0
    assert "requires --reset" in result.output
