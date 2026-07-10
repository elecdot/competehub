from __future__ import annotations

from marshmallow import Schema, fields, validate

from competehub_api.schemas.common import NonBlankString
from competehub_api.services.competition_discovery import (
    competition_tag_names,
    next_time_node,
    sorted_time_nodes,
)


class OptionalQueryText(NonBlankString):
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, str) and not value.strip():
            return None
        return super()._deserialize(value, attr, data, **kwargs)


class CompetitionListQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    keyword = OptionalQueryText(load_default=None, allow_none=True)
    category = OptionalQueryText(load_default=None, allow_none=True)
    major = OptionalQueryText(load_default=None, allow_none=True)
    grade = OptionalQueryText(load_default=None, allow_none=True)
    tag = OptionalQueryText(load_default=None, allow_none=True)
    status = OptionalQueryText(load_default=None, allow_none=True)
    participant_form = OptionalQueryText(load_default=None, allow_none=True)


class PublicCompetitionTimeNodeSchema(Schema):
    id = fields.Integer(required=True)
    node_type = fields.String(required=True)
    starts_at = fields.DateTime(allow_none=True)
    due_at = fields.DateTime(allow_none=True)
    description = fields.String(allow_none=True)


class PublicCompetitionSummarySchema(Schema):
    id = fields.Integer(required=True)
    title = fields.String(required=True)
    short_title = fields.String(allow_none=True)
    category = fields.String(allow_none=True)
    organizer = fields.String(allow_none=True)
    status = fields.Function(lambda competition: competition.status.value)
    source_name = fields.String(required=True)
    source_url = fields.String(required=True)
    official_url = fields.String(allow_none=True)
    tags = fields.Method("serialize_tags")
    suitable_majors = fields.Function(lambda competition: competition.suitable_majors or [])
    suitable_grades = fields.Function(lambda competition: competition.suitable_grades or [])
    value_notes = fields.String(allow_none=True)
    next_node = fields.Method("serialize_next_node")
    is_favorited = fields.Constant(False)
    is_subscribed = fields.Constant(False)

    def serialize_tags(self, competition):
        return competition_tag_names(competition)

    def serialize_next_node(self, competition):
        node = next_time_node(competition)
        return public_competition_time_node_schema.dump(node) if node is not None else None


class PublicCompetitionDetailSchema(PublicCompetitionSummarySchema):
    host = fields.String(allow_none=True)
    attachment_url = fields.String(allow_none=True)
    summary = fields.String(allow_none=True)
    detail = fields.String(allow_none=True)
    eligibility = fields.String(allow_none=True)
    team_size = fields.String(allow_none=True)
    participant_form = fields.String(allow_none=True)
    time_nodes = fields.Method("serialize_time_nodes")

    def serialize_time_nodes(self, competition):
        return public_competition_time_node_schema.dump(
            sorted_time_nodes(competition),
            many=True,
        )


class PublicCompetitionPageSchema(Schema):
    items = fields.List(fields.Nested(PublicCompetitionSummarySchema()), required=True)
    pagination = fields.Method("serialize_pagination")

    def serialize_pagination(self, page):
        return {
            "page": page.page,
            "page_size": page.page_size,
            "total": page.total,
        }


competition_list_query_schema = CompetitionListQuerySchema()
public_competition_time_node_schema = PublicCompetitionTimeNodeSchema()
public_competition_detail_schema = PublicCompetitionDetailSchema()
public_competition_page_schema = PublicCompetitionPageSchema()
