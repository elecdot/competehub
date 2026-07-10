from __future__ import annotations

from competehub_api.extensions import db
from competehub_api.models import StudentProfile, User


def create_default_profile(user: User) -> StudentProfile:
    return StudentProfile(
        user=user,
        interest_tags=[],
        goal_preferences=[],
        blocked_tags=[],
        default_remind_days=3,
        message_enabled=True,
    )


def update_student_profile(user: User, updates: dict) -> StudentProfile:
    profile = user.profile
    if profile is None:
        profile = create_default_profile(user)
        db.session.add(profile)

    for field, value in updates.items():
        setattr(profile, field, value)
    db.session.commit()
    return profile
