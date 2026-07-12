from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates

from competehub_api.schemas.common import StrictBoolean
from competehub_api.services.profiles import missing_fields, profile_status


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

    @validates("interest_tags")
    def validate_interest_tags(self, value, **kwargs):
        validate_interest_tags(value)


class ProfileSchema(Schema):
    id = fields.Integer(required=True)
    user_id = fields.Integer(required=True)
    college = fields.String(allow_none=True)
    major = fields.String(allow_none=True)
    grade = fields.String(allow_none=True)
    interest_tags = fields.Method("get_interest_tags")
    competition_experience = fields.String(allow_none=True)
    goal_preferences = fields.Method("get_goal_preferences")
    blocked_tags = fields.Method("get_blocked_tags")
    default_remind_days = fields.Integer(required=True)
    message_enabled = fields.Boolean(required=True)
    profile_status = fields.Method("get_profile_status")
    missing_fields = fields.Method("get_missing_fields")

    def get_profile_status(self, profile):
        return profile_status(profile)

    def get_missing_fields(self, profile):
        return missing_fields(profile)

    def get_interest_tags(self, profile):
        return list(profile.interest_tags or [])

    def get_goal_preferences(self, profile):
        return list(profile.goal_preferences or [])

    def get_blocked_tags(self, profile):
        return list(profile.blocked_tags or [])


profile_update_schema = ProfileUpdateSchema()
preference_update_schema = PreferenceUpdateSchema()
profile_schema = ProfileSchema()


def validate_interest_tags(value: list[str]) -> None:
    if len(value) > 10:
        raise ValidationError("Interest tags must contain at most 10 values.")
    if len(set(value)) != len(value):
        raise ValidationError("Interest tags must be unique.")
