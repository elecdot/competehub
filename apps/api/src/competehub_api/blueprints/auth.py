from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request, session
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from competehub_api.errors import error_response
from competehub_api.extensions import db
from competehub_api.models import StudentProfile, User
from competehub_api.models.enums import UserRole, UserStatus

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "display_name": user.display_name,
        "role": user.role.value,
    }


def success_response(data: dict, status: int = HTTPStatus.OK):
    return jsonify({"data": data, "error": None}), status


def request_json() -> dict:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def find_user_by_account(account: str | None) -> User | None:
    if not account:
        return None
    return db.session.execute(
        db.select(User).where(
            or_(User.email == account, User.phone == account, User.student_no == account)
        )
    ).scalar_one_or_none()


def get_current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_user(user: User) -> None:
    session.clear()
    session["user_id"] = user.id


@auth_bp.post("/register")
def register():
    payload = request_json()
    role = payload.get("role") or UserRole.STUDENT.value

    if role != UserRole.STUDENT.value:
        return error_response(HTTPStatus.BAD_REQUEST, "validation_error", "用户角色不合法")
    if not payload.get("password"):
        return error_response(HTTPStatus.BAD_REQUEST, "validation_error", "密码不能为空")
    if not any(payload.get(field) for field in ("email", "phone", "student_no")):
        return error_response(
            HTTPStatus.BAD_REQUEST,
            "validation_error",
            "email、phone、student_no 至少需要一个",
        )

    for field in ("email", "phone", "student_no"):
        value = payload.get(field)
        existing_user = db.session.execute(
            db.select(User).where(getattr(User, field) == value)
        ).first()
        if value and existing_user:
            return error_response(HTTPStatus.CONFLICT, "conflict", f"{field} 已存在")

    user = User(
        email=payload.get("email"),
        phone=payload.get("phone"),
        student_no=payload.get("student_no"),
        password_hash=generate_password_hash(payload["password"]),
        display_name=payload.get("display_name"),
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
    )
    if user.role == UserRole.STUDENT:
        user.profile = StudentProfile(
            interest_tags=[],
            goal_preferences=[],
            blocked_tags=[],
            default_remind_days=3,
            message_enabled=True,
        )

    db.session.add(user)
    db.session.commit()
    login_user(user)

    return success_response(user_to_dict(user), HTTPStatus.CREATED)


@auth_bp.post("/login")
def login():
    payload = request_json()
    user = find_user_by_account(payload.get("account"))

    if user is None or not check_password_hash(user.password_hash, payload.get("password") or ""):
        return error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "账号或密码错误")
    if user.status == UserStatus.DISABLED:
        return error_response(HTTPStatus.FORBIDDEN, "forbidden", "账号已禁用")

    login_user(user)

    return success_response(user_to_dict(user))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return success_response({"success": True})
