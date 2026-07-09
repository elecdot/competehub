import pytest

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import User
from competehub_api.models.enums import UserStatus


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register_student(client, email="student@example.edu"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": "13800000000",
            "student_no": "20260001",
            "password": "example-password",
            "display_name": "student a",
            "role": "student",
        },
    )


def test_register_sets_session_and_returns_current_user(client) -> None:
    response = register_student(client)

    assert response.status_code == 201
    assert response.get_json()["data"] == {
        "id": 1,
        "display_name": "student a",
        "role": "student",
    }

    me_response = client.get("/api/v1/me")

    assert me_response.status_code == 200
    assert me_response.get_json()["data"] == {
        "id": 1,
        "display_name": "student a",
        "role": "student",
    }


def test_login_logout_and_unauthorized_current_user(client) -> None:
    register_student(client)
    client.post("/api/v1/auth/logout")

    login_response = client.post(
        "/api/v1/auth/login",
        json={"account": "student@example.edu", "password": "example-password"},
    )

    assert login_response.status_code == 200
    assert login_response.get_json()["data"]["role"] == "student"

    logout_response = client.post("/api/v1/auth/logout")

    assert logout_response.status_code == 200

    me_response = client.get("/api/v1/me")

    assert me_response.status_code == 401
    assert me_response.get_json()["error"]["code"] == "unauthorized"


def test_update_and_fetch_profile(client) -> None:
    register_student(client)

    update_response = client.patch(
        "/api/v1/me/profile",
        json={
            "college": "计算机学院",
            "major": "软件工程",
            "grade": "大二",
            "interest_tags": ["人工智能", "创新创业"],
            "competition_experience": "参加过校级程序设计竞赛",
            "goal_preferences": ["保研", "能力提升"],
        },
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["data"] == {
        "id": 1,
        "user_id": 1,
        "college": "计算机学院",
        "major": "软件工程",
        "grade": "大二",
        "interest_tags": ["人工智能", "创新创业"],
        "competition_experience": "参加过校级程序设计竞赛",
        "goal_preferences": ["保研", "能力提升"],
        "blocked_tags": [],
        "default_remind_days": 3,
        "message_enabled": True,
    }

    fetch_response = client.get("/api/v1/me/profile")

    assert fetch_response.status_code == 200
    assert fetch_response.get_json() == update_response.get_json()


def test_update_preferences_returns_stable_profile_contract(client) -> None:
    register_student(client)

    response = client.patch(
        "/api/v1/me/preferences",
        json={
            "interest_tags": ["人工智能"],
            "blocked_tags": ["数学建模"],
            "default_remind_days": 5,
            "message_enabled": False,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "id": 1,
        "user_id": 1,
        "college": None,
        "major": None,
        "grade": None,
        "interest_tags": ["人工智能"],
        "competition_experience": None,
        "goal_preferences": [],
        "blocked_tags": ["数学建模"],
        "default_remind_days": 5,
        "message_enabled": False,
    }


def test_profile_requires_login(client) -> None:
    response = client.get("/api/v1/me/profile")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_disabled_user_cannot_login(client, app) -> None:
    register_student(client)
    client.post("/api/v1/auth/logout")

    with app.app_context():
        user = db.session.get(User, 1)
        user.status = UserStatus.DISABLED
        db.session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"account": "student@example.edu", "password": "example-password"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"
