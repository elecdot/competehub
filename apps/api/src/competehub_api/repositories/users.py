from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from competehub_api.extensions import db
from competehub_api.models import User, UserIdentity


def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def get_user_for_update(user_id: int) -> User | None:
    return db.session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def find_identity(identity_type: str, normalized_value: str) -> UserIdentity | None:
    return db.session.scalar(
        select(UserIdentity)
        .options(joinedload(UserIdentity.user))
        .where(
            UserIdentity.identity_type == identity_type,
            UserIdentity.normalized_value == normalized_value,
        )
    )
