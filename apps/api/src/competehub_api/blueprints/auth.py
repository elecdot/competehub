from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request, session
from marshmallow import ValidationError

from competehub_api.blueprints.responses import success_response, validation_error_response
from competehub_api.errors import error_response
from competehub_api.schemas.auth import (
    auth_capabilities_schema,
    login_schema,
    register_schema,
    resend_verification_schema,
    user_schema,
    verify_schema,
)
from competehub_api.schemas.common import load_payload
from competehub_api.services.auth import (
    authenticate_user,
    public_email_registration_available,
    register_student,
    resend_verification,
    start_session,
    verify_identity,
)
from competehub_api.services.errors import ServiceError

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.get("/capabilities")
def capabilities():
    return success_response(
        auth_capabilities_schema.dump(
            {"public_email_registration_enabled": public_email_registration_available()}
        )
    )


@auth_bp.post("/register")
def register():
    try:
        payload = load_payload(register_schema, request.get_json(silent=True))
        register_student(payload)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response({"accepted": True}, HTTPStatus.ACCEPTED)


@auth_bp.post("/verify")
def verify():
    try:
        payload = load_payload(verify_schema, request.get_json(silent=True))
        verify_identity(payload)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response({"verified": True})


@auth_bp.post("/verification/resend")
def resend():
    try:
        payload = load_payload(resend_verification_schema, request.get_json(silent=True))
        resend_verification(payload)
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    return success_response({"accepted": True}, HTTPStatus.ACCEPTED)


@auth_bp.post("/login")
def login():
    try:
        payload = load_payload(login_schema, request.get_json(silent=True))
        user = authenticate_user(payload["identity_type"], payload["identity"], payload["password"])
    except ValidationError as error:
        return validation_error_response(error)
    except ServiceError as error:
        return _service_error_response(error)

    start_session(session, user)
    return success_response(user_schema.dump(user))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return success_response({"success": True})


def _service_error_response(error: ServiceError):
    return error_response(
        error.status_code,
        error.code,
        error.message,
        error.details,
    )
