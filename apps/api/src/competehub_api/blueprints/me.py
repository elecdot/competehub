from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.models import User
from competehub_api.models.enums import UserRole
from competehub_api.schemas.auth import user_schema
from competehub_api.schemas.calendar import calendar_payload_schema, calendar_query_schema
from competehub_api.schemas.common import load_payload
from competehub_api.schemas.profile import (
    preference_update_schema,
    profile_schema,
    profile_update_schema,
)
from competehub_api.services.auth import current_user
from competehub_api.services.calendar import student_calendar
from competehub_api.services.profiles import (
    allowed_profile_options,
    student_profile_view,
    update_student_preferences,
    update_student_profile,
)

me_bp = Blueprint("me", __name__)


@me_bp.get("/me")
def get_current_user():
    user = current_user(session)
    if user is None:
        return error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "请先登录")
    return success_response(user_schema.dump(user))


@me_bp.get("/me/profile")
def get_profile():
    user, response = _require_student()
    if response is not None:
        return response
    return success_response(profile_schema.dump(student_profile_view(user)))


@me_bp.get("/me/profile/options")
def get_profile_options():
    user, response = _require_student()
    if response is not None:
        return response
    return success_response(allowed_profile_options())


@me_bp.patch("/me/profile")
def update_profile():
    return _update_profile(profile_update_schema, update_student_profile)


@me_bp.patch("/me/preferences")
def update_preferences():
    return _update_profile(preference_update_schema, update_student_preferences)


@me_bp.get("/me/calendar")
def get_calendar():
    user, response = _require_student()
    if response is not None:
        return response

    try:
        query = calendar_query_schema.load(request.args.to_dict(flat=True))
    except ValidationError as error:
        return validation_error_response(error, "calendar query is invalid")

    return success_response(
        calendar_payload_schema.dump(
            student_calendar(
                user.id,
                query["date_from"],
                query["date_to"],
                query["view"],
            )
        )
    )


def _update_profile(schema, update):
    user, response = _require_student()
    if response is not None:
        return response

    try:
        updates = load_payload(schema, request.get_json(silent=True))
    except ValidationError as error:
        return validation_error_response(error, "profile field is invalid")

    return success_response(profile_schema.dump(update(user, updates)))


def _require_student() -> tuple[User | None, object | None]:
    user = current_user(session)
    if user is None:
        return None, error_response(HTTPStatus.UNAUTHORIZED, "unauthorized", "请先登录")
    if user.role != UserRole.STUDENT:
        return None, error_response(HTTPStatus.FORBIDDEN, "forbidden", "需要学生身份")
    return user, None
