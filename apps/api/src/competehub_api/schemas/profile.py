from __future__ import annotations

from marshmallow import Schema, fields, validate

from competehub_api.schemas.common import StrictBoolean


def _string_list():
    return fields.List(fields.String(validate=validate.Length(min=1)))


class ProfileUpdateSchema(Schema):
    college = fields.String(allow_none=True)
    major = fields.String(allow_none=True)
    grade = fields.String(allow_none=True)
    interest_tags = _string_list()
    competition_experience = fields.String(allow_none=True)
    goal_preferences = _string_list()


class PreferenceUpdateSchema(Schema):
    interest_tags = _string_list()
    blocked_tags = _string_list()
    default_remind_days = fields.Integer(strict=True, validate=validate.Range(min=0))
    message_enabled = StrictBoolean()


class ProfileSchema(Schema):
    id = fields.Integer(required=True)
    user_id = fields.Integer(required=True)
    college = fields.String(allow_none=True)
    major = fields.String(allow_none=True)
    grade = fields.String(allow_none=True)
    interest_tags = _string_list()
    competition_experience = fields.String(allow_none=True)
    goal_preferences = _string_list()
    blocked_tags = _string_list()
    default_remind_days = fields.Integer(required=True)
    message_enabled = fields.Boolean(required=True)


profile_update_schema = ProfileUpdateSchema()
preference_update_schema = PreferenceUpdateSchema()
profile_schema = ProfileSchema()
