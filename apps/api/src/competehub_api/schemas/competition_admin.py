from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from competehub_api.models.enums import CompetitionStatus
from competehub_api.schemas.common import NonBlankString


def _optional_text():
    return NonBlankString(allow_none=True)


def _string_list():
    return fields.List(NonBlankString(), allow_none=True)


class CompetitionFieldsSchema(Schema):
    title = _optional_text()
    short_title = _optional_text()
    category = _optional_text()
    organizer = _optional_text()
    host = _optional_text()
    source_name = _optional_text()
    source_url = _optional_text()
    official_url = _optional_text()
    attachment_url = _optional_text()
    summary = _optional_text()
    detail = _optional_text()
    eligibility = _optional_text()
    team_size = _optional_text()
    participant_form = _optional_text()
    suitable_majors = _string_list()
    suitable_grades = _string_list()
    value_notes = _optional_text()


class CompetitionCreateSchema(CompetitionFieldsSchema):
    title = NonBlankString(required=True)
    source_name = NonBlankString(required=True)
    source_url = NonBlankString(required=True)


class CompetitionUpdateSchema(CompetitionFieldsSchema):
    title = NonBlankString()
    source_name = NonBlankString()
    source_url = NonBlankString()

    @validates_schema
    def validate_has_updates(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one editable field is required.")


class CompetitionReviewSchema(Schema):
    action = fields.String(
        required=True,
        validate=validate.OneOf(["approve", "reject", "return"]),
    )
    comment = _optional_text()


class CompetitionStatusSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(
            [
                CompetitionStatus.OFFLINE.value,
                CompetitionStatus.ARCHIVED.value,
                CompetitionStatus.CANCELLED.value,
                CompetitionStatus.EXPIRED.value,
            ]
        ),
    )
    reason = NonBlankString(required=True)


class CompetitionSchema(Schema):
    id = fields.Integer(required=True)
    title = fields.String(required=True)
    short_title = fields.String(allow_none=True)
    category = fields.String(allow_none=True)
    organizer = fields.String(allow_none=True)
    host = fields.String(allow_none=True)
    source_name = fields.String(required=True)
    source_url = fields.String(required=True)
    official_url = fields.String(allow_none=True)
    attachment_url = fields.String(allow_none=True)
    summary = fields.String(allow_none=True)
    detail = fields.String(allow_none=True)
    eligibility = fields.String(allow_none=True)
    team_size = fields.String(allow_none=True)
    participant_form = fields.String(allow_none=True)
    suitable_majors = fields.List(fields.String(), allow_none=True)
    suitable_grades = fields.List(fields.String(), allow_none=True)
    value_notes = fields.String(allow_none=True)
    status = fields.String(required=True)
    created_by_id = fields.Integer(allow_none=True)


competition_create_schema = CompetitionCreateSchema()
competition_update_schema = CompetitionUpdateSchema()
competition_review_schema = CompetitionReviewSchema()
competition_status_schema = CompetitionStatusSchema()
competition_schema = CompetitionSchema()
