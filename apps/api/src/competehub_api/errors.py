from __future__ import annotations

from http import HTTPStatus

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from competehub_api.services.errors import ServiceError


def error_response(status: int, code: str, message: str, details: dict | None = None):
    return jsonify(
        {
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
        }
    ), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ServiceError)
    def handle_service_error(error: ServiceError):
        return error_response(
            error.status_code,
            error.code,
            error.message,
            error.details,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return error_response(
            error.code or HTTPStatus.INTERNAL_SERVER_ERROR,
            error.name.lower().replace(" ", "_"),
            error.description,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        if app.config.get("TESTING"):
            raise error
        return error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "internal_server_error",
            "服务器内部错误",
        )
