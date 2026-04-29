from datetime import datetime

from flask_jwt_extended import create_access_token
from sqlalchemy import or_

from app.core.errors import AppError
from app.extensions import bcrypt, db
from app.models.user import User, UserProfile


class AuthService:
    @staticmethod
    def register(payload: dict) -> User:
        conditions = [User.username == payload["username"]]
        if payload.get("email"):
            conditions.append(User.email == payload["email"])
        if payload.get("phone"):
            conditions.append(User.phone == payload["phone"])
        if payload.get("student_no"):
            conditions.append(User.student_no == payload["student_no"])
        duplicate = User.query.filter(or_(*conditions)).first()
        if duplicate:
            raise AppError("账号、邮箱、手机号或学号已存在", 40002, 409)

        password_hash = bcrypt.generate_password_hash(payload["password"]).decode("utf-8")
        user = User(
            username=payload["username"],
            email=payload.get("email"),
            phone=payload.get("phone"),
            student_no=payload.get("student_no"),
            password_hash=password_hash,
            role=payload.get("role", "student"),
        )
        user.profile = UserProfile()
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def login(account: str, password: str) -> dict:
        user = User.query.filter(
            or_(
                User.username == account,
                User.email == account,
                User.phone == account,
                User.student_no == account,
            )
        ).first()
        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            raise AppError("账号或密码错误", 40003, 401)
        if user.status != "active":
            raise AppError("账号状态不可用", 40004, 403)

        user.last_login_at = datetime.utcnow()
        db.session.commit()

        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
        return {"access_token": token, "user": user.public_dict()}
