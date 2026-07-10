from __future__ import annotations

from http import HTTPStatus

from werkzeug.security import check_password_hash, generate_password_hash

from competehub_api.extensions import db
from competehub_api.models import User
from competehub_api.models.enums import UserRole, UserStatus
from competehub_api.repositories.users import (
    find_user_by_identity,
    find_users_by_account,
    get_user,
)
from competehub_api.services.errors import ServiceError
from competehub_api.services.profiles import create_default_profile


def register_student(payload: dict) -> User:
    for field in ("email", "phone", "student_no"):
        value = payload.get(field)
        if value and find_user_by_identity(field, value) is not None:
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "conflict",
                f"{field} already exists",
                {"field": field},
            )

    user = User(
        email=payload.get("email"),
        phone=payload.get("phone"),
        student_no=payload.get("student_no"),
        password_hash=generate_password_hash(payload["password"]),
        display_name=payload.get("display_name"),
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
    )
    user.profile = create_default_profile(user)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(account: str, password: str) -> User:
    matches = [
        user
        for user in find_users_by_account(account)
        if check_password_hash(user.password_hash, password)
    ]
    if len(matches) != 1:
        raise ServiceError(
            HTTPStatus.UNAUTHORIZED,
            "unauthorized",
            "账号或密码错误",
        )

    user = matches[0]
    if user.status == UserStatus.DISABLED:
        raise ServiceError(
            HTTPStatus.FORBIDDEN,
            "forbidden",
            "账号已禁用",
        )
    return user


def current_user(user_id: int | None) -> User | None:
    if user_id is None:
        return None
    return get_user(user_id)
