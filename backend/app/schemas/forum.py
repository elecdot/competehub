from marshmallow import EXCLUDE, Schema, fields, validate


class PostCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    content = fields.Str(required=True, validate=validate.Length(min=1))
    post_type = fields.Str(load_default="question")
    competition_id = fields.Int(allow_none=True)
    tags = fields.List(fields.Str(), load_default=list)


class CommentCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    content = fields.Str(required=True, validate=validate.Length(min=1))
    parent_id = fields.Int(allow_none=True)

