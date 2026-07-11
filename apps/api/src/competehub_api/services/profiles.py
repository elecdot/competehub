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


def ensure_student_profile(user: User) -> StudentProfile:
    if user.profile is not None:
        return user.profile
    profile = create_default_profile(user)
    db.session.add(profile)
    db.session.commit()
    return profile


def update_student_profile(user: User, updates: dict) -> StudentProfile:
    profile = user.profile
    if profile is None:
        profile = create_default_profile(user)
        db.session.add(profile)

    for field, value in updates.items():
        setattr(profile, field, value)
    db.session.commit()
    return profile


def profile_status(profile: StudentProfile) -> str:
    return "recommendation_ready" if not missing_fields(profile) else "incomplete"


def missing_fields(profile: StudentProfile) -> list[str]:
    missing = []
    if not profile.college:
        missing.append("college")
    if not profile.major:
        missing.append("major")
    if not profile.grade:
        missing.append("grade")
    if not recommendation_ready_interest_tags(profile.interest_tags):
        missing.append("interest_tags")
    return missing


def recommendation_ready_interest_tags(tags: list | None) -> bool:
    if not tags or len(tags) > 10:
        return False
    return len(set(tags)) == len(tags)
