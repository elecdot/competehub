from functools import wraps

from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.core.errors import AppError


def role_required(*allowed_roles: str):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role not in allowed_roles:
                raise AppError("权限不足", 40301, 403)
            return fn(*args, **kwargs)

        return decorated

    return wrapper

