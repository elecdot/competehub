from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from competehub_api import create_app
from competehub_api.config import ProductionConfig
from competehub_api.extensions import db
from competehub_api.models import IdentityVerificationChallenge, StudentProfile, User, UserIdentity
from competehub_api.models.enums import IdentityVerificationStatus, UserRole, UserStatus
from competehub_api.services.auth import current_user, hash_password


class InMemoryEmailSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send_verification_code(self, *, to: str, code: str) -> None:
        self.messages.append({"to": to, "code": code})

    @property
    def latest_code(self) -> str:
        return self.messages[-1]["code"]


@pytest.fixture()
def sender() -> InMemoryEmailSender:
    return InMemoryEmailSender()


@pytest.fixture()
def app(sender):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "EMAIL_VERIFICATION_SENDER": sender,
            "AUTH_RATE_LIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register_email(
    client,
    *,
    identity: str = "student@example.edu",
    password: str = "correct horse battery staple",
    display_name: str = "student a",
):
    return client.post(
        "/api/v1/auth/register",
        json={
            "identity_type": "email",
            "identity": identity,
            "password": password,
            "display_name": display_name,
        },
    )


def verify_email(client, sender, *, identity: str = "student@example.edu", code: str | None = None):
    return client.post(
        "/api/v1/auth/verify",
        json={
            "identity_type": "email",
            "identity": identity,
            "code": code or sender.latest_code,
        },
    )


def login_email(
    client,
    *,
    identity: str = "student@example.edu",
    password: str = "correct horse battery staple",
):
    return client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identity": identity,
            "password": password,
        },
    )


def provision_user(
    app,
    *,
    identity_type: str = "email",
    identity: str = "student@example.edu",
    password: str = "correct horse battery staple",
    role: UserRole = UserRole.STUDENT,
    status: UserStatus = UserStatus.ACTIVE,
    verification_status: IdentityVerificationStatus = IdentityVerificationStatus.VERIFIED,
    display_name: str = "Day 1 Student",
    capabilities: list[str] | None = None,
) -> int:
    with app.app_context():
        user = User(
            password_hash=hash_password(password, identity=identity),
            display_name=display_name,
            role=role,
            status=status,
            capabilities=capabilities or [],
        )
        user.identities.append(
            UserIdentity(
                identity_type=identity_type,
                normalized_value=identity.lower() if identity_type == "email" else identity,
                display_value=identity,
                verification_status=verification_status,
                verification_method="test_fixture",
                verified_at=datetime.now(UTC)
                if verification_status == IdentityVerificationStatus.VERIFIED
                else None,
            )
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def test_register_without_configured_sender_returns_unavailable() -> None:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "EMAIL_VERIFICATION_SENDER": None,
        }
    )
    with app.app_context():
        db.create_all()
    client = app.test_client()

    response = register_email(client)

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "registration_unavailable"
    assert client.get("/api/v1/me").status_code == 401
    with app.app_context():
        assert db.session.query(User).count() == 0
        db.session.remove()
        db.drop_all()


def test_register_email_creates_pending_identity_and_sends_hashed_code_only(
    client, app, sender
) -> None:
    response = register_email(client)

    assert response.status_code == 202
    assert response.get_json()["data"] == {"accepted": True}
    assert client.get("/api/v1/me").status_code == 401
    assert sender.messages == [{"to": "student@example.edu", "code": sender.latest_code}]

    with app.app_context():
        user = db.session.query(User).one()
        identity = db.session.query(UserIdentity).one()
        challenge = db.session.query(IdentityVerificationChallenge).one()

        assert user.status == UserStatus.PENDING_ACTIVATION
        assert identity.user_id == user.id
        assert identity.identity_type == "email"
        assert identity.normalized_value == "student@example.edu"
        assert identity.verification_status == IdentityVerificationStatus.PENDING
        assert challenge.secret_hash != sender.latest_code
        assert challenge.consumed_at is None


def test_auth_payloads_accept_documented_identifier_alias(client, sender) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "identity_type": "email",
            "identifier": "student@example.edu",
            "password": "correct horse battery staple",
            "display_name": "student a",
        },
    )
    verify_response = client.post(
        "/api/v1/auth/verify",
        json={
            "identity_type": "email",
            "identifier": "student@example.edu",
            "code": sender.latest_code,
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identifier": "student@example.edu",
            "password": "correct horse battery staple",
        },
    )

    assert register_response.status_code == 202
    assert verify_response.status_code == 200
    assert login_response.status_code == 200
    assert login_response.get_json()["data"]["role"] == "student"


def test_auth_payloads_reject_conflicting_identity_aliases(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identity": "student@example.edu",
            "identifier": "other@example.edu",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["field"] == "identity"


def test_verify_activates_account_without_creating_session(client, app, sender) -> None:
    register_email(client)

    response = verify_email(client, sender)

    assert response.status_code == 200
    assert response.get_json()["data"] == {"verified": True}
    assert client.get("/api/v1/me").status_code == 401
    with app.app_context():
        user = db.session.query(User).one()
        identity = db.session.query(UserIdentity).one()
        challenge = db.session.query(IdentityVerificationChallenge).one()

        assert user.status == UserStatus.ACTIVE
        assert identity.verification_status == IdentityVerificationStatus.VERIFIED
        assert identity.verified_at is not None
        assert challenge.consumed_at is not None


def test_verification_challenge_rejects_correct_code_after_attempt_limit(
    client, app, sender
) -> None:
    app.config["AUTH_VERIFICATION_MAX_ATTEMPTS"] = 2
    register_email(client)

    for _ in range(2):
        response = verify_email(client, sender, code="000000")
        assert response.status_code == 401

    correct_after_limit = verify_email(client, sender)

    assert correct_after_limit.status_code == 401
    assert correct_after_limit.get_json()["error"]["code"] == "unauthorized"
    with app.app_context():
        user = db.session.query(User).one()
        identity = db.session.query(UserIdentity).one()
        challenge = db.session.query(IdentityVerificationChallenge).one()

        assert user.status == UserStatus.PENDING_ACTIVATION
        assert identity.verification_status == IdentityVerificationStatus.PENDING
        assert challenge.attempt_count == 2
        assert challenge.consumed_at is None


def test_login_requires_explicit_verified_typed_identity_and_sets_versioned_session(
    client, app
) -> None:
    provision_user(app)

    response = login_email(client)

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "id": 1,
        "display_name": "Day 1 Student",
        "role": "student",
        "capabilities": [],
    }
    with client.session_transaction() as session:
        assert session["user_id"] == 1
        assert session["session_version"] == 1
        assert "issued_at" in session
        assert "last_activity_at" in session


def test_session_cookie_config_matches_auth_contract(app) -> None:
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert ProductionConfig.SESSION_COOKIE_SECURE is True


def test_student_me_always_returns_empty_capabilities(client, app) -> None:
    provision_user(app, capabilities=["competition_editor"])

    response = login_email(client)

    assert response.status_code == 200
    assert response.get_json()["data"]["capabilities"] == []


def test_login_never_cross_searches_identity_types(client, app) -> None:
    provision_user(
        app,
        identity_type="email",
        identity="shared-account",
        password="correct horse battery staple",
        display_name="Email Owner",
    )
    provision_user(
        app,
        identity_type="student_no",
        identity="shared-account",
        password="correct horse battery staple",
        display_name="Student Number Owner",
    )

    email_response = login_email(client, identity="shared-account")
    client.post("/api/v1/auth/logout")
    student_no_response = client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "student_no",
            "identity": "shared-account",
            "password": "correct horse battery staple",
        },
    )

    assert email_response.status_code == 200
    assert email_response.get_json()["data"]["display_name"] == "Email Owner"
    assert student_no_response.status_code == 200
    assert student_no_response.get_json()["data"]["display_name"] == "Student Number Owner"


@pytest.mark.parametrize(
    "user_kwargs",
    [
        {"status": UserStatus.PENDING_ACTIVATION},
        {"status": UserStatus.DISABLED},
        {"verification_status": IdentityVerificationStatus.PENDING},
    ],
)
def test_login_failures_are_generic_for_non_active_or_unverified_accounts(
    client, app, user_kwargs
) -> None:
    provision_user(app, **user_kwargs)

    response = login_email(client)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "payload",
    [
        {"identity_type": "phone", "identity": "13800000000"},
        {"identity_type": "student_no", "identity": "20260001"},
        {"identity_type": "email", "identity": "student@example.edu", "password": "short"},
        {
            "identity_type": "email",
            "identity": "student@example.edu",
            "password": "CompeteHubPassword",
        },
    ],
)
def test_register_rejects_disabled_channels_and_invalid_passwords(client, payload) -> None:
    payload.setdefault("password", "correct horse battery staple")
    payload.setdefault("display_name", "student a")

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_rate_limit_returns_429_for_repeated_login_attempts(sender) -> None:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "EMAIL_VERIFICATION_SENDER": sender,
            "AUTH_RATE_LIMIT_ENABLED": True,
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": 2,
        }
    )
    with app.app_context():
        db.create_all()
    client = app.test_client()

    for _ in range(2):
        response = login_email(client, password="wrong password value")
        assert response.status_code == 401
    limited = login_email(client, password="wrong password value")

    assert limited.status_code == 429
    assert limited.get_json()["error"]["code"] == "rate_limited"
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_rate_limit_is_scoped_by_request_source(sender) -> None:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "EMAIL_VERIFICATION_SENDER": sender,
            "AUTH_RATE_LIMIT_ENABLED": True,
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": 1,
        }
    )
    with app.app_context():
        db.create_all()
    first_client = app.test_client()
    second_client = app.test_client()

    first_response = first_client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identity": "student@example.edu",
            "password": "wrong password value",
        },
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
    )
    second_response = second_client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identity": "student@example.edu",
            "password": "wrong password value",
        },
        environ_base={"REMOTE_ADDR": "198.51.100.11"},
    )

    assert first_response.status_code == 401
    assert second_response.status_code == 401
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_rate_limit_does_not_trust_forwarded_for_by_default(sender) -> None:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "EMAIL_VERIFICATION_SENDER": sender,
            "AUTH_RATE_LIMIT_ENABLED": True,
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": 1,
        }
    )
    with app.app_context():
        db.create_all()
    client = app.test_client()

    first_response = client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identity": "student@example.edu",
            "password": "wrong password value",
        },
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    second_response = client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identity": "student@example.edu",
            "password": "wrong password value",
        },
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
        headers={"X-Forwarded-For": "203.0.113.11"},
    )

    assert first_response.status_code == 401
    assert second_response.status_code == 429
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_session_guard_rejects_disabled_version_mismatch_and_expired_sessions(client, app) -> None:
    user_id = provision_user(app)
    assert login_email(client).status_code == 200

    with app.app_context():
        user = db.session.get(User, user_id)
        user.session_version += 1
        db.session.commit()
    assert client.get("/api/v1/me").status_code == 401

    assert login_email(client).status_code == 200
    with app.app_context():
        user = db.session.get(User, user_id)
        user.status = UserStatus.DISABLED
        db.session.commit()
    assert client.get("/api/v1/me").status_code == 401

    with app.app_context():
        user = db.session.get(User, user_id)
        user.status = UserStatus.ACTIVE
        db.session.commit()
    assert login_email(client).status_code == 200
    with client.session_transaction() as session:
        expired = datetime.now(UTC) - timedelta(days=8)
        session["issued_at"] = expired.isoformat()
        session["last_activity_at"] = expired.isoformat()
    expired_response = client.get("/api/v1/me")

    assert expired_response.status_code == 401


def test_current_user_rejects_legacy_bare_user_id(app) -> None:
    user_id = provision_user(app)

    with app.app_context():
        assert current_user(user_id) is None


def test_admin_me_returns_controlled_capabilities(client, app) -> None:
    provision_user(
        app,
        identity="admin.day1@example.edu",
        role=UserRole.ADMIN,
        display_name="Day 1 Admin",
        capabilities=["competition_editor", "recommendation_editor"],
    )

    response = login_email(client, identity="admin.day1@example.edu")

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "id": 1,
        "display_name": "Day 1 Admin",
        "role": "admin",
        "capabilities": ["competition_editor", "recommendation_editor"],
    }


def test_get_profile_creates_default_incomplete_profile_for_active_student(client, app) -> None:
    provision_user(app)
    login_email(client)

    response = client.get("/api/v1/me/profile")

    assert response.status_code == 200
    assert response.get_json()["data"]["profile_status"] == "incomplete"
    assert response.get_json()["data"]["missing_fields"] == [
        "college",
        "major",
        "grade",
        "interest_tags",
    ]
    with app.app_context():
        assert db.session.query(StudentProfile).count() == 1


def test_profile_response_normalizes_null_list_fields(client, app) -> None:
    user_id = provision_user(app)
    with app.app_context():
        db.session.add(
            StudentProfile(
                user_id=user_id,
                interest_tags=None,
                goal_preferences=None,
                blocked_tags=None,
            )
        )
        db.session.commit()
    login_email(client)

    response = client.get("/api/v1/me/profile")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["interest_tags"] == []
    assert data["goal_preferences"] == []
    assert data["blocked_tags"] == []
    assert data["missing_fields"] == ["college", "major", "grade", "interest_tags"]


def test_profile_rejects_duplicate_or_too_many_interest_tags(client, app) -> None:
    provision_user(app)
    login_email(client)

    duplicate = client.patch(
        "/api/v1/me/profile",
        json={"interest_tags": ["人工智能", "人工智能"]},
    )
    too_many = client.patch(
        "/api/v1/me/profile",
        json={"interest_tags": [f"tag-{index}" for index in range(11)]},
    )

    assert duplicate.status_code == 400
    assert duplicate.get_json()["error"]["details"]["field"] == "interest_tags"
    assert too_many.status_code == 400
    assert too_many.get_json()["error"]["details"]["field"] == "interest_tags"


def test_duplicate_interest_tags_do_not_count_as_recommendation_ready(client, app) -> None:
    user_id = provision_user(app)
    with app.app_context():
        db.session.add(
            StudentProfile(
                user_id=user_id,
                college="计算机学院",
                major="软件工程",
                grade="大二",
                interest_tags=["人工智能", "人工智能"],
            )
        )
        db.session.commit()
    login_email(client)

    response = client.get("/api/v1/me/profile")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["profile_status"] == "incomplete"
    assert data["missing_fields"] == ["interest_tags"]


def test_profile_readiness_is_derived_with_stable_missing_field_order(client, app) -> None:
    provision_user(app)
    login_email(client)

    incomplete = client.patch(
        "/api/v1/me/profile",
        json={"major": "软件工程", "interest_tags": ["人工智能"]},
    )
    ready = client.patch(
        "/api/v1/me/profile",
        json={
            "college": "计算机学院",
            "grade": "大二",
        },
    )

    assert incomplete.status_code == 200
    assert incomplete.get_json()["data"]["profile_status"] == "incomplete"
    assert incomplete.get_json()["data"]["missing_fields"] == ["college", "grade"]
    assert ready.status_code == 200
    assert ready.get_json()["data"]["profile_status"] == "recommendation_ready"
    assert ready.get_json()["data"]["missing_fields"] == []
