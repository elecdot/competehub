from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates

from competehub_api.schemas.common import StrictBoolean
from competehub_api.services.profiles import (
    DEFAULT_REMINDER_NODE_TYPES,
    missing_fields,
    profile_status,
)


def _string_list():
    return fields.List(fields.String(validate=validate.Length(min=1)))


class ProfileUpdateSchema(Schema):
    college = fields.String(allow_none=True)
    major = fields.String(allow_none=True)
    grade = fields.String(allow_none=True)
    interest_tags = _string_list()
    competition_experience = fields.String(allow_none=True)
    goal_preferences = _string_list()

    @validates("interest_tags")
    def validate_interest_tags(self, value, **kwargs):
        validate_interest_tags(value)


class PreferenceUpdateSchema(Schema):
    interest_tags = _string_list()
    blocked_tags = _string_list()
    default_remind_days = fields.Integer(strict=True, validate=validate.Range(min=0))
    message_enabled = StrictBoolean()
    default_reminder_node_types = fields.List(
        fields.String(validate=validate.OneOf(DEFAULT_REMINDER_NODE_TYPES)),
        validate=validate.Length(min=1),
    )

    @validates("interest_tags")
    def validate_interest_tags(self, value, **kwargs):
        validate_interest_tags(value)

    @validates("default_reminder_node_types")
    def validate_default_reminder_node_types(self, value, **kwargs):
        if len(set(value)) != len(value):
            raise ValidationError("Reminder node types must be unique.")


class ProfileSchema(Schema):
    id = fields.Integer(required=True, attribute="profile.id")
    user_id = fields.Integer(required=True, attribute="profile.user_id")
    college = fields.String(allow_none=True, attribute="profile.college")
    major = fields.String(allow_none=True, attribute="profile.major")
    grade = fields.String(allow_none=True, attribute="profile.grade")
    interest_tags = fields.Method("get_interest_tags")
    competition_experience = fields.String(
        allow_none=True, attribute="profile.competition_experience"
    )
    goal_preferences = fields.Method("get_goal_preferences")
    blocked_tags = fields.Method("get_blocked_tags")
    default_remind_days = fields.Integer(
        required=True, attribute="reminder_settings.default_remind_days"
    )
    message_enabled = fields.Boolean(required=True, attribute="reminder_settings.enabled")
    default_reminder_node_types = fields.Method("get_default_reminder_node_types")
    profile_status = fields.Method("get_profile_status")
    missing_fields = fields.Method("get_missing_fields")

    def get_profile_status(self, view):
        return profile_status(view.profile)

    def get_missing_fields(self, view):
        return missing_fields(view.profile)

    def get_interest_tags(self, view):
        return list(view.profile.interest_tags or [])

    def get_goal_preferences(self, view):
        return list(view.profile.goal_preferences or [])

    def get_blocked_tags(self, view):
        return list(view.profile.blocked_tags or [])

    def get_default_reminder_node_types(self, view):
        return list(view.reminder_settings.node_types or [])


profile_update_schema = ProfileUpdateSchema()
preference_update_schema = PreferenceUpdateSchema()
profile_schema = ProfileSchema()


def validate_interest_tags(value: list[str]) -> None:
    if len(value) > 10:
        raise ValidationError("Interest tags must contain at most 10 values.")
    if len(set(value)) != len(value):
        raise ValidationError("Interest tags must be unique.")
