from __future__ import annotations

import secrets
import unicodedata
from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from flask import current_app, request
from redis import Redis
from sqlalchemy import select, update
from werkzeug.security import check_password_hash, generate_password_hash

from competehub_api.extensions import db
from competehub_api.identity_normalization import normalize_identity_value
from competehub_api.models import (
    IdentityVerificationChallenge,
    User,
    UserIdentity,
    VerificationDeliveryOutbox,
)
from competehub_api.models.enums import IdentityVerificationStatus, UserRole, UserStatus
from competehub_api.repositories.users import find_identity, get_user
from competehub_api.services.errors import ServiceError
from competehub_api.services.passwords import (
    create_password_hash,
    password_hash_needs_upgrade,
    verify_password_hash,
)
from competehub_api.services.profiles import create_missing_student_profile
from competehub_api.services.verification_delivery import derive_verification_code

WEAK_PASSWORDS = {
    "password",
    "password123456789",
    "competehubpassword",
    "competehub123456",
    "student123456789",
}

SESSION_TIMEOUTS = {
    UserRole.STUDENT: (timedelta(hours=24), timedelta(days=7)),
    UserRole.ADMIN: (timedelta(minutes=30), timedelta(hours=8)),
}
SESSION_ACTIVITY_REFRESH_INTERVAL = timedelta(minutes=1)

RATE_LIMIT_INCREMENT_SCRIPT = """
local count = redis.call("INCR", KEYS[1])
if redis.call("TTL", KEYS[1]) < 0 then
    redis.call("EXPIRE", KEYS[1], tonumber(ARGV[1]))
end
return count
"""

DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=19456,t=2,p=1$GrwzQDiQxvi+JlFbriwXyQ$"
    "CSpzXZps9pSajrLWn0EyqWtfEr19WWKJGcpHlX86w3A"
)
DUMMY_CHALLENGE_HASH = (
    "scrypt:32768:8:1$S3eRBlkoQ2uapB1s$"
    "9fe920e799c1f7dc902d5f4bf5638f1555d723ec799169a3d5591a45fc2ebfa8"
    "df650832df79520aa7ccbc7871b702db10b32920f8abddabc51b7a609bda18bf"
)


@dataclass(frozen=True)
class PreparedVerificationChallenge:
    secret_hash: str
    delivery_nonce: str


def register_student(payload: dict) -> None:
    _require_registration_sender()

    _check_rate_limit("register", payload["identity_type"], payload["identity"])
    identity_type = payload["identity_type"]
    display_value = payload["identity"]
    normalized_value = normalize_identity(identity_type, display_value)
    normalized_password = normalize_password(payload["password"])
    validate_password(normalized_password, identity=normalized_value)
    password_hash = create_password_hash(normalized_password)
    prepared_challenge = _prepare_verification_challenge()

    existing = find_identity(identity_type, normalized_value)
    if existing is not None:
        return

    user = User(
        email=display_value if identity_type == "email" else None,
        password_hash=password_hash,
        display_name=payload.get("display_name"),
        role=UserRole.STUDENT,
        status=UserStatus.PENDING_ACTIVATION,
        capabilities=[],
    )
    identity = UserIdentity(
        identity_type=identity_type,
        normalized_value=normalized_value,
        display_value=display_value,
        verification_status=IdentityVerificationStatus.PENDING,
        verification_method="email_code",
    )
    user.identities.append(identity)
    db.session.add(user)
    db.session.flush()
    _create_challenge_and_delivery(identity, prepared_challenge)
    db.session.commit()


def verify_identity(payload: dict) -> None:
    _check_rate_limit("verify", payload["identity_type"], payload["identity"])
    identity = _find_identity_for_update(
        payload["identity_type"],
        normalize_identity(payload["identity_type"], payload["identity"]),
    )
    identity_is_eligible = (
        identity is not None
        and identity.verification_status == IdentityVerificationStatus.PENDING
        and identity.user.status == UserStatus.PENDING_ACTIVATION
    )
    challenge = _latest_active_challenge_for_update(identity) if identity is not None else None
    challenge_is_eligible = (
        challenge is not None and challenge.attempt_count < _verification_attempt_limit()
    )
    code_matches = check_password_hash(
        challenge.secret_hash if challenge_is_eligible else DUMMY_CHALLENGE_HASH,
        payload["code"],
    )
    if not identity_is_eligible or not challenge_is_eligible or not code_matches:
        if challenge_is_eligible:
            challenge.attempt_count += 1
            db.session.commit()
        raise _generic_auth_error()

    now = _utcnow()
    _consume_unconsumed_challenges(identity, now)
    challenge.attempt_count += 1
    identity.verification_status = IdentityVerificationStatus.VERIFIED
    identity.verified_at = now
    identity.user.status = UserStatus.ACTIVE
    if identity.user.role == UserRole.STUDENT:
        create_missing_student_profile(identity.user)
    db.session.commit()


def resend_verification(payload: dict) -> None:
    _require_registration_sender()

    _check_rate_limit("resend", payload["identity_type"], payload["identity"])
    identity = _find_identity_for_update(
        payload["identity_type"],
        normalize_identity(payload["identity_type"], payload["identity"]),
    )
    prepared_challenge = _prepare_verification_challenge()
    if (
        identity is not None
        and identity.verification_status == IdentityVerificationStatus.PENDING
        and identity.user.status == UserStatus.PENDING_ACTIVATION
    ):
        _consume_unconsumed_challenges(identity, _utcnow())
        _create_challenge_and_delivery(identity, prepared_challenge)
        db.session.commit()


def authenticate_user(identity_type: str, identity_value: str, password: str) -> User:
    _check_rate_limit("login", identity_type, identity_value)
    identity = find_identity(identity_type, normalize_identity(identity_type, identity_value))
    normalized_password = normalize_password(password)
    user = identity.user if identity is not None else None
    password_matches = verify_password_hash(
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
        normalized_password,
    )
    identity_is_eligible = (
        identity is not None
        and user is not None
        and user.status == UserStatus.ACTIVE
        and identity.verification_status == IdentityVerificationStatus.VERIFIED
    )
    if not identity_is_eligible or not password_matches:
        raise _generic_auth_error()

    if password_hash_needs_upgrade(user.password_hash):
        user.password_hash = create_password_hash(normalized_password)
        db.session.commit()
    return user


def hash_password(password: str, *, identity: str | None = None) -> str:
    normalized = normalize_password(password)
    validate_password(normalized, identity=identity)
    return create_password_hash(normalized)


def normalize_password(password: str) -> str:
    return unicodedata.normalize("NFC", password)


def validate_password(password: str, *, identity: str | None = None) -> None:
    normalized = normalize_password(password)
    length = len(normalized)
    weak_values = set(WEAK_PASSWORDS)
    if identity:
        weak_values.add(identity.casefold())
    if length < 15 or length > 128 or normalized.casefold() in weak_values:
        raise ServiceError(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "password does not satisfy policy",
            {"field": "password"},
        )


def normalize_identity(identity_type: str, value: str) -> str:
    try:
        return normalize_identity_value(identity_type, value)
    except ValueError as error:
        raise _identity_validation_error("identity") from error


def terminate_all_sessions(user: User) -> None:
    increment_session_version(user)


def apply_account_governance_change(
    user: User,
    *,
    role: UserRole | None = None,
    status: UserStatus | None = None,
    capabilities: list[str] | None = None,
) -> None:
    if role is not None:
        user.role = role
    if status is not None:
        user.status = status
    if capabilities is not None:
        user.capabilities = capabilities
    increment_session_version(user)


def increment_session_version(user: User) -> None:
    user.session_version += 1


def start_session(session_data: MutableMapping, user: User) -> None:
    now = _utcnow().isoformat()
    session_data.clear()
    session_data["user_id"] = user.id
    session_data["session_version"] = user.session_version
    session_data["issued_at"] = now
    session_data["last_activity_at"] = now


def current_user(session_data: MutableMapping | None) -> User | None:
    if session_data is None or not isinstance(session_data, MutableMapping):
        return None

    user_id = session_data.get("user_id")
    version = session_data.get("session_version")
    issued_at = _parse_session_time(session_data.get("issued_at"))
    last_activity_at = _parse_session_time(session_data.get("last_activity_at"))
    if user_id is None or version is None or issued_at is None or last_activity_at is None:
        session_data.clear()
        return None

    user = get_user(user_id)
    if user is None or user.status != UserStatus.ACTIVE or user.session_version != version:
        session_data.clear()
        return None

    idle_timeout, absolute_timeout = SESSION_TIMEOUTS.get(
        user.role,
        SESSION_TIMEOUTS[UserRole.STUDENT],
    )
    now = _utcnow()
    if now - last_activity_at > idle_timeout or now - issued_at > absolute_timeout:
        session_data.clear()
        return None

    if now - last_activity_at >= SESSION_ACTIVITY_REFRESH_INTERVAL:
        session_data["last_activity_at"] = now.isoformat()
    return user


def _prepare_verification_challenge() -> PreparedVerificationChallenge:
    delivery_nonce = secrets.token_hex(32)
    code = derive_verification_code(delivery_nonce)
    return PreparedVerificationChallenge(
        secret_hash=generate_password_hash(code, method="scrypt:32768:8:1"),
        delivery_nonce=delivery_nonce,
    )


def _create_challenge_and_delivery(
    identity: UserIdentity,
    prepared: PreparedVerificationChallenge,
) -> None:
    challenge = IdentityVerificationChallenge(
        identity=identity,
        secret_hash=prepared.secret_hash,
        expires_at=_utcnow() + timedelta(minutes=15),
    )
    challenge.delivery = VerificationDeliveryOutbox(
        delivery_nonce=prepared.delivery_nonce,
        available_at=_utcnow(),
    )
    db.session.add(challenge)


def _require_registration_sender() -> None:
    sender = current_app.config.get("EMAIL_VERIFICATION_SENDER")
    if not current_app.config.get("PUBLIC_EMAIL_REGISTRATION_ENABLED") or sender is None:
        raise ServiceError(
            HTTPStatus.SERVICE_UNAVAILABLE,
            "registration_unavailable",
            "public registration is unavailable",
        )


def _find_identity_for_update(identity_type: str, normalized_value: str) -> UserIdentity | None:
    return db.session.scalar(
        select(UserIdentity)
        .join(User, User.id == UserIdentity.user_id)
        .where(
            UserIdentity.identity_type == identity_type,
            UserIdentity.normalized_value == normalized_value,
        )
        .with_for_update()
    )


def _latest_active_challenge_for_update(
    identity: UserIdentity,
) -> IdentityVerificationChallenge | None:
    now = _utcnow()
    return db.session.scalar(
        select(IdentityVerificationChallenge)
        .where(
            IdentityVerificationChallenge.user_identity_id == identity.id,
            IdentityVerificationChallenge.consumed_at.is_(None),
            IdentityVerificationChallenge.expires_at > now,
        )
        .order_by(
            IdentityVerificationChallenge.created_at.desc(),
            IdentityVerificationChallenge.id.desc(),
        )
        .limit(1)
        .with_for_update()
    )


def _consume_unconsumed_challenges(identity: UserIdentity, consumed_at: datetime) -> None:
    db.session.execute(
        update(IdentityVerificationChallenge)
        .where(
            IdentityVerificationChallenge.user_identity_id == identity.id,
            IdentityVerificationChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=consumed_at)
    )


def _verification_attempt_limit() -> int:
    return current_app.config.get("AUTH_VERIFICATION_MAX_ATTEMPTS", 5)


def _check_rate_limit(action: str, identity_type: str, identity: str) -> None:
    if not current_app.config.get("AUTH_RATE_LIMIT_ENABLED", True):
        return
    max_attempts = current_app.config.get("AUTH_RATE_LIMIT_MAX_ATTEMPTS", 10)
    window_seconds = current_app.config.get("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60)
    normalized_identity = normalize_identity(identity_type, identity)
    keys = (
        f"auth-rate:{action}:identity:{identity_type}:{normalized_identity}",
        f"auth-rate:{action}:source:{_request_source()}",
    )
    for key in keys:
        count = _increment_rate_limit_key(key, window_seconds)
        if count > max_attempts:
            raise ServiceError(
                HTTPStatus.TOO_MANY_REQUESTS,
                "rate_limited",
                "too many attempts",
            )


def _increment_rate_limit_key(key: str, window_seconds: int) -> int:
    store = _rate_limit_store()
    return int(store.eval(RATE_LIMIT_INCREMENT_SCRIPT, 1, key, window_seconds))


def _rate_limit_store():
    configured_store = current_app.config.get("AUTH_RATE_LIMIT_STORE")
    if configured_store is not None:
        return configured_store
    if "auth_rate_limit_redis" not in current_app.extensions:
        current_app.extensions["auth_rate_limit_redis"] = Redis.from_url(
            current_app.config["REDIS_URL"],
            decode_responses=True,
        )
    return current_app.extensions["auth_rate_limit_redis"]


def _request_source() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if current_app.config.get("AUTH_TRUST_PROXY_HEADERS", False) and forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def _identity_validation_error(field: str) -> ServiceError:
    return ServiceError(
        HTTPStatus.BAD_REQUEST,
        "validation_error",
        "identity is invalid",
        {"field": field},
    )


def _parse_session_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return _ensure_aware(parsed)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _generic_auth_error() -> ServiceError:
    return ServiceError(
        HTTPStatus.UNAUTHORIZED,
        "unauthorized",
        "账号或密码错误",
    )
