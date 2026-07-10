from __future__ import annotations

from http import HTTPStatus

from flask import jsonify
from marshmallow import ValidationError

from competehub_api.errors import error_response


def success_response(data: dict, status: int = HTTPStatus.OK):
    return jsonify({"data": data, "error": None}), status


def validation_error_response(
    error: ValidationError,
    message: str = "request body is invalid",
):
    field = next(iter(error.messages), "_schema") if isinstance(error.messages, dict) else "_schema"
    return error_response(
        HTTPStatus.BAD_REQUEST,
        "validation_error",
        message,
        {"field": field},
    )
