from marshmallow import EXCLUDE, Schema, fields


class RecommendationPreferenceSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    preferred_tags = fields.List(fields.Str(), load_default=list)
    blocked_tags = fields.List(fields.Str(), load_default=list)
    preferred_levels = fields.List(fields.Str(), load_default=list)
    weights = fields.Dict(load_default=dict)

