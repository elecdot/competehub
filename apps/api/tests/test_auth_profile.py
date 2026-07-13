from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

import competehub_api.services.auth as auth_service
import competehub_api.services.profiles as profile_service
from competehub_api import create_app
from competehub_api.config import ProductionConfig
from competehub_api.extensions import db
from competehub_api.models import (
    IdentityVerificationChallenge,
    Reminder,
    ReminderSetting,
    StudentProfile,
    Subscription,
    User,
    UserIdentity,
    VerificationDeliveryOutbox,
)
from competehub_api.models.enums import (
    IdentityVerificationStatus,
    ReminderStatus,
    SubscriptionStatus,
    UserRole,
    UserStatus,
)
from competehub_api.services.auth import (
    apply_account_governance_change,
    current_user,
    hash_password,
    terminate_all_sessions,
)
from competehub_api.services.profiles import provision_student_owned_rows
from competehub_api.services.verification_delivery import dispatch_verification_deliveries


class InMemoryEmailSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send_verification_code(self, *, to: str, code: str) -> None:
        self.messages.append({"to": to, "code": code})

    @property
    def latest_code(self) -> str:
        return self.messages[-1]["code"]


class FakeRedisRateLimitStore:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def eval(self, _script: str, num_keys: int, key: str, window_seconds: int) -> int:
        assert num_keys == 1
        self.values[key] = self.values.get(key, 0) + 1
        if key not in self.expirations:
            self.expirations[key] = int(window_seconds)
        return self.values[key]


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
            "PUBLIC_EMAIL_REGISTRATION_ENABLED": True,
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


def dispatch_verification_email(app) -> dict[str, int]:
    with app.app_context():
        return dispatch_verification_deliveries()


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
        db.session.flush()
        if role == UserRole.STUDENT:
            provision_student_owned_rows(user)
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


def test_register_email_queues_pending_identity_and_worker_sends_hashed_code_only(
    client, app, sender
) -> None:
    response = register_email(client)

    assert response.status_code == 202
    assert response.get_json()["data"] == {"accepted": True}
    assert client.get("/api/v1/me").status_code == 401
    assert sender.messages == []

    with app.app_context():
        user = db.session.query(User).one()
        identity = db.session.query(UserIdentity).one()
        challenge = db.session.query(IdentityVerificationChallenge).one()
        delivery = db.session.query(VerificationDeliveryOutbox).one()

        assert user.status == UserStatus.PENDING_ACTIVATION
        assert identity.user_id == user.id
        assert identity.identity_type == "email"
        assert identity.normalized_value == "student@example.edu"
        assert identity.verification_status == IdentityVerificationStatus.PENDING
        assert challenge.consumed_at is None
        assert delivery.challenge_id == challenge.id
        assert delivery.delivery_nonce is not None
        assert delivery.delivered_at is None

    assert dispatch_verification_email(app) == {"delivered": 1, "discarded": 0, "failed": 0}
    assert sender.messages == [{"to": "student@example.edu", "code": sender.latest_code}]
    with app.app_context():
        challenge = db.session.query(IdentityVerificationChallenge).one()
        delivery = db.session.query(VerificationDeliveryOutbox).one()
        assert challenge.secret_hash != sender.latest_code
        assert delivery.delivery_nonce is None
        assert delivery.delivered_at is not None


def test_auth_payloads_accept_documented_identifier_alias(client, app, sender) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "identity_type": "email",
            "identifier": "student@example.edu",
            "password": "correct horse battery staple",
            "display_name": "student a",
        },
    )
    dispatch_verification_email(app)
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
    dispatch_verification_email(app)

    response = verify_email(client, sender)

    assert response.status_code == 200
    assert response.get_json()["data"] == {"verified": True}
    assert client.get("/api/v1/me").status_code == 401
    with app.app_context():
        user = db.session.query(User).one()
        identity = db.session.query(UserIdentity).one()
        challenge = db.session.query(IdentityVerificationChallenge).one()
        profile = db.session.query(StudentProfile).one()
        settings = db.session.query(ReminderSetting).one()

        assert user.status == UserStatus.ACTIVE
        assert identity.verification_status == IdentityVerificationStatus.VERIFIED
        assert identity.verified_at is not None
        assert challenge.consumed_at is not None
        assert profile.user_id == user.id
        assert profile.college is None
        assert profile.interest_tags == []
        assert settings.user_id == user.id
        assert settings.enabled is True
        assert settings.default_remind_days == 3
        assert settings.node_types == [
            "registration_deadline",
            "submission_deadline",
            "competition_start",
        ]


def test_verification_challenge_rejects_correct_code_after_attempt_limit(
    client, app, sender
) -> None:
    app.config["AUTH_VERIFICATION_MAX_ATTEMPTS"] = 2
    register_email(client)
    dispatch_verification_email(app)

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


def test_resend_invalidates_the_previous_verification_code(client, app, sender) -> None:
    register_email(client)
    dispatch_verification_email(app)
    previous_code = sender.latest_code

    resend = client.post(
        "/api/v1/auth/verification/resend",
        json={"identity_type": "email", "identity": "student@example.edu"},
    )
    assert len(sender.messages) == 1
    dispatch_verification_email(app)
    current_code = sender.latest_code

    assert resend.status_code == 202
    assert verify_email(client, sender, code=previous_code).status_code == 401
    assert verify_email(client, sender, code=current_code).status_code == 200


def test_resend_before_worker_discards_the_older_queued_delivery(client, app, sender) -> None:
    register_email(client)
    resend = client.post(
        "/api/v1/auth/verification/resend",
        json={"identity_type": "email", "identity": "student@example.edu"},
    )

    assert resend.status_code == 202
    assert sender.messages == []
    assert dispatch_verification_email(app) == {"delivered": 1, "discarded": 1, "failed": 0}
    assert len(sender.messages) == 1
    assert verify_email(client, sender).status_code == 200


def test_verification_delivery_failure_remains_retryable(client, app, sender) -> None:
    class UnavailableSender:
        def send_verification_code(self, *, to: str, code: str) -> None:
            raise ConnectionError("smtp unavailable")

    app.config["EMAIL_VERIFICATION_SENDER"] = UnavailableSender()
    register_email(client)

    assert dispatch_verification_email(app) == {"delivered": 0, "discarded": 0, "failed": 1}
    with app.app_context():
        delivery = db.session.query(VerificationDeliveryOutbox).one()
        assert delivery.attempt_count == 1
        assert delivery.delivery_nonce is not None
        assert delivery.last_error == "ConnectionError"
        delivery.available_at = datetime.now(UTC) - timedelta(seconds=1)
        db.session.commit()

    app.config["EMAIL_VERIFICATION_SENDER"] = sender
    assert dispatch_verification_email(app) == {"delivered": 1, "discarded": 0, "failed": 0}
    assert len(sender.messages) == 1


def test_consumed_or_old_code_cannot_reactivate_a_disabled_account(client, app, sender) -> None:
    register_email(client)
    dispatch_verification_email(app)
    previous_code = sender.latest_code
    client.post(
        "/api/v1/auth/verification/resend",
        json={"identity_type": "email", "identity": "student@example.edu"},
    )
    dispatch_verification_email(app)

    assert verify_email(client, sender).status_code == 200
    with app.app_context():
        user = db.session.query(User).one()
        user.status = UserStatus.DISABLED
        db.session.commit()

    replay = verify_email(client, sender, code=previous_code)

    assert replay.status_code == 401
    with app.app_context():
        user = db.session.query(User).one()
        challenges = db.session.query(IdentityVerificationChallenge).all()
        assert user.status == UserStatus.DISABLED
        assert all(challenge.consumed_at is not None for challenge in challenges)


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


def test_new_password_hash_uses_explicit_argon2id_baseline() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


def test_successful_legacy_scrypt_login_upgrades_password_hash(client, app) -> None:
    user_id = provision_user(app)
    legacy_hash = generate_password_hash(
        "correct horse battery staple",
        method="scrypt:32768:8:1",
    )
    with app.app_context():
        user = db.session.get(User, user_id)
        user.password_hash = legacy_hash
        db.session.commit()

    response = login_email(client)

    assert response.status_code == 200
    with app.app_context():
        upgraded_hash = db.session.get(User, user_id).password_hash
        assert upgraded_hash != legacy_hash
        assert upgraded_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


def test_wrong_password_does_not_upgrade_legacy_scrypt_hash(client, app) -> None:
    user_id = provision_user(app)
    legacy_hash = generate_password_hash(
        "correct horse battery staple",
        method="scrypt:32768:8:1",
    )
    with app.app_context():
        user = db.session.get(User, user_id)
        user.password_hash = legacy_hash
        db.session.commit()

    response = login_email(client, password="wrong password value")

    assert response.status_code == 401
    with app.app_context():
        assert db.session.get(User, user_id).password_hash == legacy_hash


def test_current_argon2id_hash_is_not_rehashed_on_login(client, app) -> None:
    user_id = provision_user(app)
    with app.app_context():
        original_hash = db.session.get(User, user_id).password_hash

    response = login_email(client)

    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(User, user_id).password_hash == original_hash


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


@pytest.mark.parametrize("account_state", ["unknown", "pending", "disabled", "active"])
def test_failed_login_always_runs_one_argon2_grade_password_verification(
    client, app, monkeypatch, account_state
) -> None:
    if account_state != "unknown":
        provision_user(
            app,
            status=(
                UserStatus.PENDING_ACTIVATION
                if account_state == "pending"
                else UserStatus.DISABLED
                if account_state == "disabled"
                else UserStatus.ACTIVE
            ),
            verification_status=(
                IdentityVerificationStatus.PENDING
                if account_state == "pending"
                else IdentityVerificationStatus.VERIFIED
            ),
        )
    verification_hashes: list[str] = []

    def record_verification(password_hash: str, _password: str) -> bool:
        verification_hashes.append(password_hash)
        return False

    monkeypatch.setattr(auth_service, "verify_password_hash", record_verification)

    response = login_email(client, password="wrong password value")

    assert response.status_code == 401
    assert len(verification_hashes) == 1
    assert verification_hashes[0].startswith("$argon2id$")


@pytest.mark.parametrize("identity_state", ["unknown", "pending_without_challenge", "disabled"])
def test_failed_verification_always_runs_one_challenge_hash_check(
    client, app, monkeypatch, identity_state
) -> None:
    if identity_state != "unknown":
        provision_user(
            app,
            status=(
                UserStatus.PENDING_ACTIVATION
                if identity_state == "pending_without_challenge"
                else UserStatus.DISABLED
            ),
            verification_status=IdentityVerificationStatus.PENDING,
        )
    verification_hashes: list[str] = []

    def record_verification(password_hash: str, _code: str) -> bool:
        verification_hashes.append(password_hash)
        return False

    monkeypatch.setattr(auth_service, "check_password_hash", record_verification)

    response = client.post(
        "/api/v1/auth/verify",
        json={
            "identity_type": "email",
            "identity": "student@example.edu",
            "code": "000000",
        },
    )

    assert response.status_code == 401
    assert len(verification_hashes) == 1
    assert verification_hashes[0].startswith("scrypt:32768:8:1$")


def test_existing_registration_runs_password_and_challenge_hash_work(
    client, app, monkeypatch
) -> None:
    provision_user(app)
    password_hash_calls = 0
    challenge_hash_calls = 0
    original_password_hash = auth_service.create_password_hash
    original_challenge_hash = auth_service.generate_password_hash

    def record_password_hash(password: str) -> str:
        nonlocal password_hash_calls
        password_hash_calls += 1
        return original_password_hash(password)

    def record_challenge_hash(code: str, *, method: str) -> str:
        nonlocal challenge_hash_calls
        challenge_hash_calls += 1
        return original_challenge_hash(code, method=method)

    monkeypatch.setattr(auth_service, "create_password_hash", record_password_hash)
    monkeypatch.setattr(auth_service, "generate_password_hash", record_challenge_hash)

    response = register_email(client)

    assert response.status_code == 202
    assert password_hash_calls == 1
    assert challenge_hash_calls == 1


def test_unknown_resend_runs_challenge_hash_work(client, monkeypatch) -> None:
    challenge_hash_calls = 0
    original_challenge_hash = auth_service.generate_password_hash

    def record_challenge_hash(code: str, *, method: str) -> str:
        nonlocal challenge_hash_calls
        challenge_hash_calls += 1
        return original_challenge_hash(code, method=method)

    monkeypatch.setattr(auth_service, "generate_password_hash", record_challenge_hash)

    response = client.post(
        "/api/v1/auth/verification/resend",
        json={"identity_type": "email", "identity": "unknown@example.edu"},
    )

    assert response.status_code == 202
    assert challenge_hash_calls == 1


def test_registration_request_does_not_call_smtp_sender(client, sender) -> None:
    response = register_email(client)

    assert response.status_code == 202
    assert sender.messages == []


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
            "AUTH_RATE_LIMIT_STORE": FakeRedisRateLimitStore(),
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


def test_rate_limit_limits_identity_across_request_sources(sender) -> None:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "EMAIL_VERIFICATION_SENDER": sender,
            "AUTH_RATE_LIMIT_ENABLED": True,
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": 1,
            "AUTH_RATE_LIMIT_STORE": FakeRedisRateLimitStore(),
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
    assert second_response.status_code == 429
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_rate_limit_limits_request_source_across_identities(sender) -> None:
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "EMAIL_VERIFICATION_SENDER": sender,
            "AUTH_RATE_LIMIT_ENABLED": True,
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": 1,
            "AUTH_RATE_LIMIT_STORE": FakeRedisRateLimitStore(),
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
    )
    second_response = client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "email",
            "identity": "other@example.edu",
            "password": "wrong password value",
        },
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
    )

    assert first_response.status_code == 401
    assert second_response.status_code == 429
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
            "AUTH_RATE_LIMIT_STORE": FakeRedisRateLimitStore(),
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


def test_session_version_boundaries_increment_for_governance_changes(app) -> None:
    user_id = provision_user(app)

    with app.app_context():
        user = db.session.get(User, user_id)
        apply_account_governance_change(
            user,
            role=UserRole.ADMIN,
            status=UserStatus.DISABLED,
            capabilities=["competition_editor"],
        )
        assert user.session_version == 2
        terminate_all_sessions(user)
        assert user.session_version == 3


@pytest.mark.parametrize(
    ("role", "session_field", "timeout"),
    [
        (UserRole.STUDENT, "last_activity_at", timedelta(hours=24)),
        (UserRole.STUDENT, "issued_at", timedelta(days=7)),
        (UserRole.ADMIN, "last_activity_at", timedelta(minutes=30)),
        (UserRole.ADMIN, "issued_at", timedelta(hours=8)),
    ],
)
def test_role_specific_session_timeout_boundaries(app, role, session_field, timeout) -> None:
    provision_user(app, role=role)
    client = app.test_client()

    assert login_email(client).status_code == 200
    with client.session_transaction() as session:
        session[session_field] = (datetime.now(UTC) - timeout + timedelta(seconds=5)).isoformat()
    assert client.get("/api/v1/me").status_code == 200

    assert login_email(client).status_code == 200
    with client.session_transaction() as session:
        session[session_field] = (datetime.now(UTC) - timeout - timedelta(seconds=1)).isoformat()
    assert client.get("/api/v1/me").status_code == 401


def test_authenticated_activity_coalesces_idle_timestamp_cookie_writes(app) -> None:
    provision_user(app)
    client = app.test_client()
    assert login_email(client).status_code == 200

    with client.session_transaction() as session:
        initial_activity = session["last_activity_at"]
    assert client.get("/api/v1/me").status_code == 200
    with client.session_transaction() as session:
        assert session["last_activity_at"] == initial_activity
        stale_activity = datetime.now(UTC) - timedelta(minutes=2)
        session["last_activity_at"] = stale_activity.isoformat()

    assert client.get("/api/v1/me").status_code == 200
    with client.session_transaction() as session:
        assert datetime.fromisoformat(session["last_activity_at"]) > stale_activity


def test_logout_only_ends_one_of_two_browser_sessions(app) -> None:
    provision_user(app)
    first_browser = app.test_client()
    second_browser = app.test_client()
    assert login_email(first_browser).status_code == 200
    assert login_email(second_browser).status_code == 200

    assert first_browser.post("/api/v1/auth/logout").status_code == 200

    assert first_browser.get("/api/v1/me").status_code == 401
    assert second_browser.get("/api/v1/me").status_code == 200


def test_terminate_all_ends_both_browser_sessions(app) -> None:
    user_id = provision_user(app)
    first_browser = app.test_client()
    second_browser = app.test_client()
    assert login_email(first_browser).status_code == 200
    assert login_email(second_browser).status_code == 200

    with app.app_context():
        user = db.session.get(User, user_id)
        terminate_all_sessions(user)
        db.session.commit()

    assert first_browser.get("/api/v1/me").status_code == 401
    assert second_browser.get("/api/v1/me").status_code == 401


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


def test_get_profile_reads_activation_profile_without_writing(client, app) -> None:
    register_email(client)
    dispatch_verification_email(app)
    verify_email(client, app.config["EMAIL_VERIFICATION_SENDER"])
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
    assert response.get_json()["data"] == {
        "id": 1,
        "user_id": 1,
        "college": None,
        "major": None,
        "grade": None,
        "interest_tags": [],
        "competition_experience": None,
        "goal_preferences": [],
        "blocked_tags": [],
        "message_enabled": True,
        "default_remind_days": 3,
        "default_reminder_node_types": [
            "registration_deadline",
            "submission_deadline",
            "competition_start",
        ],
        "profile_status": "incomplete",
        "missing_fields": ["college", "major", "grade", "interest_tags"],
    }
    with app.app_context():
        assert db.session.query(StudentProfile).count() == 1
        assert db.session.query(ReminderSetting).count() == 1


def test_get_profile_missing_required_rows_returns_internal_error_without_lazy_creation(
    client, app
) -> None:
    user_id = provision_user(app)
    with app.app_context():
        user = db.session.get(User, user_id)
        db.session.delete(user.profile)
        db.session.delete(user.reminder_settings)
        db.session.commit()
    login_email(client)

    response = client.get("/api/v1/me/profile")

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
    with app.app_context():
        assert db.session.query(StudentProfile).count() == 0
        assert db.session.query(ReminderSetting).count() == 0


def test_profile_and_preferences_patches_return_combined_authoritative_response(
    client, app, sender
) -> None:
    register_email(client)
    dispatch_verification_email(app)
    verify_email(client, sender)
    login_email(client)

    profile_response = client.patch(
        "/api/v1/me/profile",
        json={"competition_experience": "school-level programming contest"},
    )
    preferences_response = client.patch(
        "/api/v1/me/preferences",
        json={
            "message_enabled": False,
            "default_remind_days": 7,
            "default_reminder_node_types": [
                "competition_start",
                "registration_deadline",
            ],
        },
    )

    assert profile_response.status_code == 200
    assert profile_response.get_json()["data"]["message_enabled"] is True
    assert profile_response.get_json()["data"]["default_remind_days"] == 3
    assert profile_response.get_json()["data"]["default_reminder_node_types"] == [
        "registration_deadline",
        "submission_deadline",
        "competition_start",
    ]
    assert preferences_response.status_code == 200
    assert preferences_response.get_json()["data"]["competition_experience"] == (
        "school-level programming contest"
    )
    assert preferences_response.get_json()["data"]["message_enabled"] is False
    assert preferences_response.get_json()["data"]["default_remind_days"] == 7
    assert preferences_response.get_json()["data"]["default_reminder_node_types"] == [
        "registration_deadline",
        "competition_start",
    ]
    with app.app_context():
        profile = db.session.query(StudentProfile).one()
        settings = db.session.query(ReminderSetting).one()
        assert profile.competition_experience == "school-level programming contest"
        assert settings.enabled is False
        assert settings.default_remind_days == 7
        assert settings.node_types == ["registration_deadline", "competition_start"]


def _add_reminder_preference_plans(app, user_id: int) -> tuple[int, list[int]]:
    other_user_id = provision_user(app, identity="other-student@example.edu")
    with app.app_context():
        db.session.add_all(
            [
                Subscription(
                    id=1,
                    user_id=user_id,
                    competition_id=101,
                    status=SubscriptionStatus.ACTIVE,
                    reminder_enabled=True,
                    remind_days=5,
                    node_types=["registration_deadline"],
                    reminder_confirmed_at=datetime(2026, 7, 1, tzinfo=UTC),
                ),
                Reminder(
                    id=1,
                    user_id=user_id,
                    competition_id=101,
                    time_node_snapshot_id=101,
                    logical_node_key="own-pending-a",
                    time_node_revision=1,
                    node_type="registration_deadline",
                    due_at=datetime(2026, 8, 1, tzinfo=UTC),
                    title="pending a",
                    status=ReminderStatus.PENDING,
                ),
                Reminder(
                    id=2,
                    user_id=user_id,
                    competition_id=101,
                    time_node_snapshot_id=102,
                    logical_node_key="own-pending-b",
                    time_node_revision=1,
                    node_type="submission_deadline",
                    due_at=datetime(2026, 8, 2, tzinfo=UTC),
                    title="pending b",
                    status=ReminderStatus.PENDING,
                ),
                Reminder(
                    id=3,
                    user_id=user_id,
                    competition_id=101,
                    time_node_snapshot_id=103,
                    logical_node_key="own-sent",
                    time_node_revision=1,
                    node_type="competition_start",
                    due_at=datetime(2026, 8, 3, tzinfo=UTC),
                    title="sent",
                    status=ReminderStatus.SENT,
                    sent_at=datetime(2026, 7, 2, tzinfo=UTC),
                ),
                Reminder(
                    id=4,
                    user_id=user_id,
                    competition_id=101,
                    time_node_snapshot_id=104,
                    logical_node_key="own-failed",
                    time_node_revision=1,
                    node_type="competition_start",
                    due_at=datetime(2026, 8, 4, tzinfo=UTC),
                    title="failed",
                    status=ReminderStatus.FAILED,
                    failed_at=datetime(2026, 7, 3, tzinfo=UTC),
                    last_error_code="delivery_failed",
                ),
                Reminder(
                    id=5,
                    user_id=other_user_id,
                    competition_id=101,
                    time_node_snapshot_id=105,
                    logical_node_key="other-pending",
                    time_node_revision=1,
                    node_type="registration_deadline",
                    due_at=datetime(2026, 8, 5, tzinfo=UTC),
                    title="other pending",
                    status=ReminderStatus.PENDING,
                ),
            ]
        )
        db.session.commit()
    return other_user_id, [1, 2]


def test_preferences_global_disable_cancels_only_own_pending_plans(client, app) -> None:
    user_id = provision_user(app)
    other_user_id, pending_ids = _add_reminder_preference_plans(app, user_id)
    login_email(client)

    response = client.patch("/api/v1/me/preferences", json={"message_enabled": False})

    assert response.status_code == 200
    assert response.get_json()["data"]["message_enabled"] is False
    with app.app_context():
        settings = db.session.query(ReminderSetting).filter_by(user_id=user_id).one()
        subscription = db.session.query(Subscription).filter_by(user_id=user_id).one()
        pending = db.session.query(Reminder).filter(Reminder.id.in_(pending_ids)).all()
        sent = db.session.get(Reminder, 3)
        failed = db.session.get(Reminder, 4)
        other = db.session.get(Reminder, 5)
        assert settings.enabled is False
        assert [(reminder.status, reminder.cancel_reason) for reminder in pending] == [
            (ReminderStatus.CANCELLED, "global_reminder_disabled"),
            (ReminderStatus.CANCELLED, "global_reminder_disabled"),
        ]
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.reminder_enabled is True
        assert subscription.remind_days == 5
        assert subscription.node_types == ["registration_deadline"]
        assert subscription.reminder_confirmed_at == datetime(2026, 7, 1)
        assert sent.status == ReminderStatus.SENT
        assert sent.sent_at == datetime(2026, 7, 2)
        assert failed.status == ReminderStatus.FAILED
        assert failed.failed_at == datetime(2026, 7, 3)
        assert failed.last_error_code == "delivery_failed"
        assert other.user_id == other_user_id
        assert other.status == ReminderStatus.PENDING
        assert other.cancel_reason is None


def test_preferences_global_disable_is_idempotent_and_enable_does_not_restore_plans(
    client, app
) -> None:
    user_id = provision_user(app)
    _, pending_ids = _add_reminder_preference_plans(app, user_id)
    login_email(client)

    first_disable = client.patch("/api/v1/me/preferences", json={"message_enabled": False})
    assert first_disable.status_code == 200
    with app.app_context():
        cancelled_at = {
            reminder.id: reminder.updated_at
            for reminder in db.session.query(Reminder).filter(Reminder.id.in_(pending_ids))
        }
    repeated_disable = client.patch("/api/v1/me/preferences", json={"message_enabled": False})
    enable = client.patch("/api/v1/me/preferences", json={"message_enabled": True})
    assert repeated_disable.status_code == 200
    assert enable.status_code == 200

    with app.app_context():
        settings = db.session.query(ReminderSetting).filter_by(user_id=user_id).one()
        pending = db.session.query(Reminder).filter(Reminder.id.in_(pending_ids)).all()
        assert settings.enabled is True
        assert [(reminder.status, reminder.cancel_reason) for reminder in pending] == [
            (ReminderStatus.CANCELLED, "global_reminder_disabled"),
            (ReminderStatus.CANCELLED, "global_reminder_disabled"),
        ]
        assert {reminder.id: reminder.updated_at for reminder in pending} == cancelled_at


def test_preferences_global_disable_rolls_back_if_plan_cancellation_fails(
    client, app, monkeypatch
) -> None:
    user_id = provision_user(app)
    _, pending_ids = _add_reminder_preference_plans(app, user_id)
    login_email(client)

    def fail_after_cancellation(reminders):
        reminders[0].status = ReminderStatus.CANCELLED
        raise RuntimeError("cancellation failed")

    monkeypatch.setattr(profile_service, "_cancel_pending_reminders", fail_after_cancellation)

    with pytest.raises(RuntimeError, match="cancellation failed"):
        client.patch("/api/v1/me/preferences", json={"message_enabled": False})

    with app.app_context():
        settings = db.session.query(ReminderSetting).filter_by(user_id=user_id).one()
        pending = db.session.query(Reminder).filter(Reminder.id.in_(pending_ids)).all()
        assert settings.enabled is True
        assert all(reminder.status == ReminderStatus.PENDING for reminder in pending)
        assert all(reminder.cancel_reason is None for reminder in pending)


def test_preferences_missing_required_rows_returns_internal_error_without_lazy_creation(
    client, app
) -> None:
    user_id = provision_user(app)
    with app.app_context():
        user = db.session.get(User, user_id)
        db.session.delete(user.reminder_settings)
        db.session.commit()
    login_email(client)

    response = client.patch("/api/v1/me/preferences", json={"message_enabled": False})

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
    with app.app_context():
        assert db.session.query(ReminderSetting).filter_by(user_id=user_id).count() == 0


def test_profile_response_normalizes_null_list_fields(client, app) -> None:
    user_id = provision_user(app)
    with app.app_context():
        profile = db.session.query(StudentProfile).filter_by(user_id=user_id).one()
        profile.interest_tags = None
        profile.goal_preferences = None
        profile.blocked_tags = None
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


def test_profile_rejects_values_outside_controlled_dictionary(client, app) -> None:
    provision_user(app)
    login_email(client)

    invalid_college = client.patch(
        "/api/v1/me/profile",
        json={
            "college": "不存在学院",
            "major": "软件工程",
            "grade": "大二",
            "interest_tags": ["人工智能"],
        },
    )
    invalid_major_relation = client.patch(
        "/api/v1/me/profile",
        json={
            "college": "计算机学院",
            "major": "金融学",
            "grade": "大二",
            "interest_tags": ["人工智能"],
        },
    )
    invalid_tag = client.patch(
        "/api/v1/me/profile",
        json={
            "college": "计算机学院",
            "major": "软件工程",
            "grade": "大二",
            "interest_tags": ["不存在标签"],
        },
    )

    assert invalid_college.status_code == 400
    assert invalid_college.get_json()["error"]["details"]["field"] == "college"
    assert invalid_major_relation.status_code == 400
    assert invalid_major_relation.get_json()["error"]["details"]["field"] == "major"
    assert invalid_tag.status_code == 400
    assert invalid_tag.get_json()["error"]["details"]["field"] == "interest_tags"


def test_invalid_existing_dictionary_values_do_not_count_as_recommendation_ready(
    client, app
) -> None:
    user_id = provision_user(app)
    with app.app_context():
        profile = db.session.query(StudentProfile).filter_by(user_id=user_id).one()
        profile.college = "不存在学院"
        profile.major = "不存在专业"
        profile.grade = "大二"
        profile.interest_tags = ["不存在标签"]
        db.session.commit()
    login_email(client)

    response = client.get("/api/v1/me/profile")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["profile_status"] == "incomplete"
    assert data["missing_fields"] == ["college", "major", "interest_tags"]


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


def test_phone_identity_normalizes_to_e164_for_login(client, app) -> None:
    provision_user(
        app,
        identity_type="phone",
        identity="+8613800000000",
        password="correct horse battery staple",
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "identity_type": "phone",
            "identity": "+86 138 0000 0000",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200
