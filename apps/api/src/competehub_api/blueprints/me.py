from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request

from competehub_api.blueprints.auth import get_current_user, success_response, user_to_dict
from competehub_api.errors import error_response
from competehub_api.extensions import db
from competehub_api.models import StudentProfile, User
from competehub_api.models.enums import UserRole

me_bp = Blueprint("me", __name__)

PROFILE_FIELDS = {
    "college",
    "major",
    "grade",
    "interest_tags",
    "competition_experience",
    "goal_preferences",
}

PREFERENCE_FIELDS = {
    "interest_tags",
    "blocked_tags",
    "default_remind_days",
    "message_enabled",
}

LIST_FIELDS = {"interest_tags", "goal_preferences", "blocked_tags"}
TEXT_FIELDS = {"college", "major", "grade", "competition_experience"}


def request_json() -> dict:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def require_user() -> User | None:
    user = get_current_user()
    if user is None:
        return None
    return user


def require_student_profile():
    user = require_user()
    if user is None:
        return None, error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "请先登录")
    if user.role != UserRole.STUDENT:
        return None, error_response(HTTPStatus.FORBIDDEN, "forbidden", "需要学生身份")

    profile = user.profile
    if profile is None:
        profile = StudentProfile(
            user=user,
            interest_tags=[],
            goal_preferences=[],
            blocked_tags=[],
            default_remind_days=3,
            message_enabled=True,
        )
        db.session.add(profile)
        db.session.commit()

    return profile, None


def normalize_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else []


def profile_to_dict(profile: StudentProfile) -> dict:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "college": profile.college,
        "major": profile.major,
        "grade": profile.grade,
        "interest_tags": normalize_list(profile.interest_tags),
        "competition_experience": profile.competition_experience,
        "goal_preferences": normalize_list(profile.goal_preferences),
        "blocked_tags": normalize_list(profile.blocked_tags),
        "default_remind_days": profile.default_remind_days,
        "message_enabled": profile.message_enabled,
    }


def apply_allowed_fields(
    profile: StudentProfile,
    payload: dict,
    allowed_fields: set[str],
) -> str | None:
    updates = {}
    for field in allowed_fields:
        if field not in payload:
            continue
        value = payload[field]
        if field in TEXT_FIELDS and value is not None and not isinstance(value, str):
            return field
        if field in LIST_FIELDS and (
            not isinstance(value, list)
            or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            return field
        if field == "default_remind_days":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return field
        if field == "message_enabled" and not isinstance(value, bool):
            return field
        updates[field] = value

    for field, value in updates.items():
        setattr(profile, field, value)
    return None


def profile_validation_error(field: str):
    return error_response(
        HTTPStatus.BAD_REQUEST,
        "validation_error",
        "profile field is invalid",
        {"field": field},
    )


@me_bp.get("/me")
def current_user():
    user = require_user()
    if user is None:
        return error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "请先登录")
    return success_response(user_to_dict(user))


@me_bp.get("/me/profile")
def get_profile():
    profile, response = require_student_profile()
    if response is not None:
        return response
    return success_response(profile_to_dict(profile))


@me_bp.patch("/me/profile")
def update_profile():
    profile, response = require_student_profile()
    if response is not None:
        return response

    invalid_field = apply_allowed_fields(profile, request_json(), PROFILE_FIELDS)
    if invalid_field is not None:
        return profile_validation_error(invalid_field)
    db.session.commit()

    return success_response(profile_to_dict(profile))


@me_bp.patch("/me/preferences")
def update_preferences():
    profile, response = require_student_profile()
    if response is not None:
        return response

    invalid_field = apply_allowed_fields(profile, request_json(), PREFERENCE_FIELDS)
    if invalid_field is not None:
        return profile_validation_error(invalid_field)
    db.session.commit()

    return success_response(profile_to_dict(profile))
