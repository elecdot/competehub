from flask import Blueprint, request

from app.core.response import success
from app.schemas.auth import LoginSchema, RegisterSchema
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    payload = RegisterSchema().load(request.get_json() or {})
    user = AuthService.register(payload)
    return success(user.public_dict(), "注册成功", status=201)


@auth_bp.post("/login")
def login():
    payload = LoginSchema().load(request.get_json() or {})
    data = AuthService.login(payload["account"], payload["password"])
    return success(data, "登录成功")

