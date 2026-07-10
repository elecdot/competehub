from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.schemas.auth import login_schema, register_schema, user_schema
from competehub_api.schemas.common import load_payload
from competehub_api.services.auth import authenticate_user, register_student
from competehub_api.services.errors import ServiceError

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    try:
        payload = load_payload(register_schema, request.get_json(silent=True))
        user = register_student(payload)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    _login_user(user.id)
    return success_response(user_schema.dump(user), HTTPStatus.CREATED)


@auth_bp.post("/login")
def login():
    try:
        payload = load_payload(login_schema, request.get_json(silent=True))
        user = authenticate_user(payload["account"], payload["password"])
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    _login_user(user.id)
    return success_response(user_schema.dump(user))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return success_response({"success": True})


def _login_user(user_id: int) -> None:
    session.clear()
    session["user_id"] = user_id


def _service_error_response(error: ServiceError):
    return error_response(
        error.status_code,
        error.code,
        error.message,
        error.details,
    )
