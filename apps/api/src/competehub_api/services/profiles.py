from __future__ import annotations

from http import HTTPStatus

from flask import current_app

from competehub_api.extensions import db
from competehub_api.models import StudentProfile, User
from competehub_api.services.errors import ServiceError


def create_default_profile(user: User) -> StudentProfile:
    return StudentProfile(
        user=user,
        interest_tags=[],
        goal_preferences=[],
        blocked_tags=[],
        default_remind_days=3,
        message_enabled=True,
    )


def create_missing_student_profile(user: User) -> StudentProfile:
    if user.profile is not None:
        return user.profile
    profile = create_default_profile(user)
    db.session.add(profile)
    return profile


def update_student_profile(user: User, updates: dict) -> StudentProfile:
    profile = user.profile
    if profile is None:
        raise ServiceError(
            HTTPStatus.NOT_FOUND,
            "profile_not_found",
            "student profile is not provisioned",
        )

    validate_profile_update(profile, updates)
    for field, value in updates.items():
        setattr(profile, field, value)
    db.session.commit()
    return profile


def profile_status(profile: StudentProfile) -> str:
    return "recommendation_ready" if not missing_fields(profile) else "incomplete"


def missing_fields(profile: StudentProfile) -> list[str]:
    missing = []
    if not _is_allowed_college(profile.college):
        missing.append("college")
    if not _is_present_and_valid_major(profile.college, profile.major):
        missing.append("major")
    if not _is_allowed_grade(profile.grade):
        missing.append("grade")
    if not recommendation_ready_interest_tags(profile.interest_tags):
        missing.append("interest_tags")
    return missing


def recommendation_ready_interest_tags(tags: list | None) -> bool:
    return bool(tags) and _has_only_allowed_interest_tags(tags)


def validate_profile_update(profile: StudentProfile, updates: dict) -> None:
    candidate = {
        "college": profile.college,
        "major": profile.major,
        "grade": profile.grade,
        "interest_tags": profile.interest_tags,
    }
    candidate.update(
        {
            key: value
            for key, value in updates.items()
            if key in {"college", "major", "grade", "interest_tags"}
        }
    )
    validate_controlled_profile_fields(candidate, require_complete=False)


def validate_controlled_profile_fields(profile: dict, *, require_complete: bool) -> None:
    """Validate real and synthetic recommendation profile facts from one dictionary."""
    college = profile.get("college")
    major = profile.get("major")
    grade = profile.get("grade")
    interest_tags = profile.get("interest_tags")
    if (require_complete or college is not None) and not _is_allowed_college(college):
        raise _profile_validation_error("college")
    if (require_complete or major is not None) and not _is_present_and_valid_major(college, major):
        raise _profile_validation_error("major")
    if (require_complete or grade is not None) and not _is_allowed_grade(grade):
        raise _profile_validation_error("grade")
    if require_complete:
        if not recommendation_ready_interest_tags(interest_tags):
            raise _profile_validation_error("interest_tags")
    elif interest_tags is not None and not _has_only_allowed_interest_tags(interest_tags):
        raise _profile_validation_error("interest_tags")


def allowed_profile_options() -> dict:
    return {
        "colleges": list(_majors_by_college()),
        "majors_by_college": {
            college: list(majors) for college, majors in _majors_by_college().items()
        },
        "grades": list(_allowed_grades()),
        "interest_tags": list(_allowed_interest_tags()),
    }


def _is_allowed_college(value: str | None) -> bool:
    return bool(value) and value in _majors_by_college()


def _is_allowed_major(college: str | None, major: str | None) -> bool:
    if not major or not college:
        return False
    return major in _majors_by_college().get(college, ())


def _is_present_and_valid_major(college: str | None, major: str | None) -> bool:
    if not major:
        return False
    if college:
        return _is_allowed_major(college, major)
    return any(major in majors for majors in _majors_by_college().values())


def _is_allowed_grade(value: str | None) -> bool:
    return bool(value) and value in _allowed_grades()


def _has_only_allowed_interest_tags(tags: list) -> bool:
    return (
        len(tags) <= 10
        and len(set(tags)) == len(tags)
        and all(tag in _allowed_interest_tags() for tag in tags)
    )


def _majors_by_college() -> dict[str, tuple[str, ...]]:
    return current_app.config["PROFILE_ALLOWED_MAJORS_BY_COLLEGE"]


def _allowed_grades() -> tuple[str, ...]:
    return current_app.config["PROFILE_ALLOWED_GRADES"]


def _allowed_interest_tags() -> tuple[str, ...]:
    return current_app.config["PROFILE_ALLOWED_INTEREST_TAGS"]


def _profile_validation_error(field: str) -> ServiceError:
    return ServiceError(
        HTTPStatus.BAD_REQUEST,
        "validation_error",
        "profile field is outside the controlled dictionary",
        {"field": field},
    )
