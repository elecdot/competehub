from __future__ import annotations

from marshmallow import Schema, fields

from competehub_api.schemas.competition_public import PublicCompetitionSummarySchema


class RecommendationItemSchema(Schema):
    position = fields.Integer(required=True)
    reason_codes = fields.List(fields.String(), required=True)
    reasons = fields.List(fields.String(), required=True)
    competition = fields.Nested(PublicCompetitionSummarySchema(), required=True)


class RecommendationFeedSchema(Schema):
    recommendation_mode = fields.Function(lambda feed: feed.context.mode.value)
    profile_status = fields.Function(lambda feed: feed.context.profile_status, allow_none=True)
    missing_fields = fields.Function(lambda feed: list(feed.context.missing_fields))
    fallback_reason = fields.Function(
        lambda feed: feed.context.fallback_cause.value if feed.context.fallback_cause else None,
        allow_none=True,
    )
    rule_set_version = fields.Function(lambda feed: feed.context.rule_set_version, allow_none=True)
    items = fields.List(fields.Nested(RecommendationItemSchema()), required=True)


recommendation_feed_schema = RecommendationFeedSchema()
