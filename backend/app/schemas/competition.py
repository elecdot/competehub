from marshmallow import EXCLUDE, Schema, fields, validate


class CompetitionCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    summary = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    category = fields.Str(required=True)
    level = fields.Str(required=True)
    organizer = fields.Str(allow_none=True)
    target_majors = fields.List(fields.Str(), load_default=list)
    target_grades = fields.List(fields.Str(), load_default=list)
    tags = fields.List(fields.Str(), load_default=list)
    registration_start_at = fields.DateTime(allow_none=True)
    registration_deadline_at = fields.DateTime(allow_none=True)
    competition_start_at = fields.DateTime(allow_none=True)
    competition_end_at = fields.DateTime(allow_none=True)
    official_url = fields.Url(allow_none=True)
    attachment_url = fields.Str(allow_none=True)


class CompetitionUpdateSchema(CompetitionCreateSchema):
    title = fields.Str(validate=validate.Length(min=2, max=200))
    category = fields.Str()
    level = fields.Str()
    status = fields.Str(validate=validate.OneOf(["draft", "pending", "published", "archived", "rejected"]))

