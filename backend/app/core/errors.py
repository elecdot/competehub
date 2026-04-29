from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.core.response import fail


class AppError(Exception):
    def __init__(self, message: str, code: int = 40000, status: int = 400):
        self.message = message
        self.code = code
        self.status = status


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return fail(error.message, error.code, error.status)

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return fail("参数校验失败", 40001, 422, error.messages)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return fail(error.description, error.code or 40000, error.code or 500)

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error: SQLAlchemyError):
        app.logger.exception(error)
        return fail("数据库操作失败", 50001, 500)

    @app.errorhandler(Exception)
    def handle_unknown_error(error: Exception):
        app.logger.exception(error)
        return fail("服务器内部错误", 50000, 500)

