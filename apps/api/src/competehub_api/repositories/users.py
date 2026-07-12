from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from competehub_api.extensions import db
from competehub_api.models import User, UserIdentity


def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def find_identity(identity_type: str, normalized_value: str) -> UserIdentity | None:
    return db.session.scalar(
        select(UserIdentity)
        .options(joinedload(UserIdentity.user))
        .where(
            UserIdentity.identity_type == identity_type,
            UserIdentity.normalized_value == normalized_value,
        )
    )
