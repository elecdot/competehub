from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus

from flask import current_app
from sqlalchemy import func, select

from competehub_api.extensions import db
from competehub_api.models import Reminder, ReminderSetting, StudentProfile, User
from competehub_api.models.enums import ReminderStatus
from competehub_api.services.errors import ServiceError
from competehub_api.subscription_node_types import (
    SUBSCRIPTION_NODE_TYPES,
    canonical_subscription_node_types,
)

DEFAULT_REMINDER_NODE_TYPES = list(SUBSCRIPTION_NODE_TYPES)


@dataclass(frozen=True)
class StudentProfileView:
    profile: StudentProfile
    reminder_settings: ReminderSetting


def create_default_profile(user: User) -> StudentProfile:
    return StudentProfile(
        user=user,
        interest_tags=[],
        goal_preferences=[],
        blocked_tags=[],
    )


def create_default_reminder_settings(user: User) -> ReminderSetting:
    if db.session.get_bind().dialect.name == "sqlite":
        db.session.flush()
        setting_id = db.session.scalar(select(func.coalesce(func.max(ReminderSetting.id), 0) + 1))
        return ReminderSetting(
            id=setting_id,
            user_id=user.id,
            enabled=True,
            default_remind_days=3,
            node_types=list(SUBSCRIPTION_NODE_TYPES),
        )
    return ReminderSetting(
        user_id=user.id,
        enabled=True,
        default_remind_days=3,
        node_types=list(SUBSCRIPTION_NODE_TYPES),
    )


def provision_student_owned_rows(user: User) -> None:
    """Provision required student rows inside the caller's transaction."""
    if user.profile is None:
        db.session.add(create_default_profile(user))
    if user.reminder_settings is None:
        db.session.add(create_default_reminder_settings(user))


def student_profile_view(user: User) -> StudentProfileView:
    profile = user.profile
    reminder_settings = user.reminder_settings
    if profile is None or reminder_settings is None:
        db.session.rollback()
        raise ServiceError(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "internal_server_error",
            "student-owned profile data is missing",
        )
    return StudentProfileView(profile=profile, reminder_settings=reminder_settings)


def update_student_profile(user: User, updates: dict) -> StudentProfileView:
    view = student_profile_view(user)
    profile = view.profile
    validate_profile_update(profile, updates)
    for field, value in updates.items():
        setattr(profile, field, value)
    db.session.commit()
    return view


def update_student_preferences(user: User, updates: dict) -> StudentProfileView:
    try:
        profile = db.session.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        reminder_settings = db.session.scalar(
            select(ReminderSetting).where(ReminderSetting.user_id == user.id).with_for_update()
        )
        if profile is None or reminder_settings is None:
            raise ServiceError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_server_error",
                "student-owned profile data is missing",
            )

        disables_global_reminders = (
            updates.get("message_enabled") is False and reminder_settings.enabled is True
        )
        pending_reminders = []
        if disables_global_reminders:
            pending_reminders = list(
                db.session.scalars(
                    select(Reminder)
                    .where(
                        Reminder.user_id == user.id,
                        Reminder.status == ReminderStatus.PENDING,
                    )
                    .order_by(Reminder.id)
                    .with_for_update()
                )
            )

        profile_updates = {
            field: value
            for field, value in updates.items()
            if field in {"interest_tags", "blocked_tags"}
        }
        validate_profile_update(profile, profile_updates)
        for field, value in profile_updates.items():
            setattr(profile, field, value)

        if "message_enabled" in updates:
            reminder_settings.enabled = updates["message_enabled"]
        if disables_global_reminders:
            _cancel_pending_reminders(pending_reminders)
        if "default_remind_days" in updates:
            reminder_settings.default_remind_days = updates["default_remind_days"]
        if "default_reminder_node_types" in updates:
            reminder_settings.node_types = canonical_subscription_node_types(
                updates["default_reminder_node_types"]
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return StudentProfileView(profile=profile, reminder_settings=reminder_settings)


def _cancel_pending_reminders(reminders: list[Reminder]) -> None:
    for reminder in reminders:
        reminder.status = ReminderStatus.CANCELLED
        reminder.cancel_reason = "global_reminder_disabled"


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
    if candidate["college"] is not None and not _is_allowed_college(candidate["college"]):
        raise _profile_validation_error("college")
    if candidate["major"] is not None and not _is_present_and_valid_major(
        candidate["college"], candidate["major"]
    ):
        raise _profile_validation_error("major")
    if candidate["grade"] is not None and not _is_allowed_grade(candidate["grade"]):
        raise _profile_validation_error("grade")
    if candidate["interest_tags"] is not None and not _has_only_allowed_interest_tags(
        candidate["interest_tags"]
    ):
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
