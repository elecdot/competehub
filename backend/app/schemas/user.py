from marshmallow import EXCLUDE, Schema, fields


class ProfileSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    real_name = fields.Str(allow_none=True)
    school = fields.Str(allow_none=True)
    college = fields.Str(allow_none=True)
    major = fields.Str(allow_none=True)
    grade = fields.Str(allow_none=True)
    interests = fields.List(fields.Str(), load_default=list)
    competition_experiences = fields.List(fields.Dict(), load_default=list)
    goals = fields.List(fields.Str(), load_default=list)
    ability_level = fields.Str(load_default="beginner")
    avatar_url = fields.Str(allow_none=True)

