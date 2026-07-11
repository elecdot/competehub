import pytest
from werkzeug.security import generate_password_hash

from competehub_api import create_app
from competehub_api.extensions import db
from competehub_api.models import StudentProfile, User
from competehub_api.models.enums import UserRole, UserStatus


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


def register_student(
    client,
    email="student@example.edu",
    phone="13800000000",
    student_no="20260001",
    password="example-password",
):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": phone,
            "student_no": student_no,
            "password": password,
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
        "capabilities": [],
    }

    me_response = client.get("/api/v1/me")

    assert me_response.status_code == 200
    assert me_response.get_json()["data"] == {
        "id": 1,
        "display_name": "student a",
        "role": "student",
        "capabilities": [],
    }


def test_register_rejects_admin_role(client, app) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.edu",
            "password": "example-password",
            "display_name": "Untrusted Admin",
            "role": "admin",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"
    with app.app_context():
        assert db.session.query(User).count() == 0


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


def test_login_disambiguates_cross_field_account_with_password(client) -> None:
    register_student(client, email="shared-account", password="first-password")
    client.post("/api/v1/auth/logout")
    register_student(
        client,
        email="second@example.edu",
        phone="13900000000",
        student_no="shared-account",
        password="second-password",
    )
    client.post("/api/v1/auth/logout")

    first_login = client.post(
        "/api/v1/auth/login",
        json={"account": "shared-account", "password": "first-password"},
    )
    client.post("/api/v1/auth/logout")
    second_login = client.post(
        "/api/v1/auth/login",
        json={"account": "shared-account", "password": "second-password"},
    )

    assert first_login.status_code == 200
    assert first_login.get_json()["data"]["id"] == 1
    assert second_login.status_code == 200
    assert second_login.get_json()["data"]["id"] == 2


def test_login_rejects_ambiguous_cross_field_credentials(client) -> None:
    register_student(client, email="shared-account", password="shared-password")
    client.post("/api/v1/auth/logout")
    register_student(
        client,
        email="second@example.edu",
        phone="13900000000",
        student_no="shared-account",
        password="shared-password",
    )
    client.post("/api/v1/auth/logout")

    response = client.post(
        "/api/v1/auth/login",
        json={"account": "shared-account", "password": "shared-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_auth_rejects_non_object_and_invalid_typed_json(client) -> None:
    register_response = client.post("/api/v1/auth/register", json=["not", "an", "object"])
    login_response = client.post(
        "/api/v1/auth/login",
        json={"account": ["student@example.edu"], "password": "example-password"},
    )

    assert register_response.status_code == 400
    assert register_response.get_json()["error"]["code"] == "validation_error"
    assert login_response.status_code == 400
    assert login_response.get_json()["error"]["code"] == "validation_error"


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


@pytest.mark.parametrize(
    ("endpoint", "payload", "field"),
    [
        ("/api/v1/me/profile", {"major": ["软件工程"]}, "major"),
        ("/api/v1/me/preferences", {"interest_tags": "人工智能"}, "interest_tags"),
        (
            "/api/v1/me/preferences",
            {"interest_tags": ["人工智能", 42]},
            "interest_tags",
        ),
        ("/api/v1/me/preferences", {"default_remind_days": -1}, "default_remind_days"),
        (
            "/api/v1/me/preferences",
            {"default_remind_days": "three"},
            "default_remind_days",
        ),
        ("/api/v1/me/preferences", {"message_enabled": "false"}, "message_enabled"),
    ],
)
def test_profile_updates_reject_invalid_field_types(client, endpoint, payload, field) -> None:
    register_student(client)

    response = client.patch(endpoint, json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == {
        "code": "validation_error",
        "message": "profile field is invalid",
        "details": {"field": field},
    }


def test_profile_updates_are_isolated_to_current_session_user(client) -> None:
    register_student(client)
    client.patch("/api/v1/me/profile", json={"major": "软件工程"})
    client.post("/api/v1/auth/logout")

    register_student(
        client,
        email="second@example.edu",
        phone="13900000000",
        student_no="20260002",
    )
    client.patch("/api/v1/me/profile", json={"major": "计算机科学与技术"})
    second_profile = client.get("/api/v1/me/profile")

    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login",
        json={"account": "student@example.edu", "password": "example-password"},
    )
    first_profile = client.get("/api/v1/me/profile")

    assert second_profile.get_json()["data"]["major"] == "计算机科学与技术"
    assert first_profile.get_json()["data"]["major"] == "软件工程"


def test_get_profile_does_not_create_missing_profile(client, app) -> None:
    with app.app_context():
        user = User(
            email="legacy-student@example.edu",
            password_hash=generate_password_hash("example-password"),
            display_name="Legacy Student",
            role=UserRole.STUDENT,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get("/api/v1/me/profile")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
    with app.app_context():
        assert db.session.query(StudentProfile).count() == 0


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
