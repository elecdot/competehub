from __future__ import annotations

from sqlalchemy import or_, select

from competehub_api.extensions import db
from competehub_api.models import User

IDENTITY_COLUMNS = {
    "email": User.email,
    "phone": User.phone,
    "student_no": User.student_no,
}


def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def find_user_by_identity(field: str, value: str) -> User | None:
    return db.session.scalar(select(User).where(IDENTITY_COLUMNS[field] == value))


def find_users_by_account(account: str) -> list[User]:
    statement = (
        select(User)
        .where(or_(User.email == account, User.phone == account, User.student_no == account))
        .order_by(User.id)
    )
    return list(db.session.scalars(statement))
