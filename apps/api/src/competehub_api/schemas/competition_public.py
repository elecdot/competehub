from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from competehub_api.models.enums import ParticipantForm
from competehub_api.schemas.common import NonBlankString, UtcDateTime
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
    participant_form = OptionalQueryText(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf([*[form.value for form in ParticipantForm], None]),
    )
    deadline_from = fields.Date(load_default=None, allow_none=True)
    deadline_to = fields.Date(load_default=None, allow_none=True)

    @validates_schema
    def validate_deadline_range(self, data, **kwargs):
        deadline_from = data.get("deadline_from")
        deadline_to = data.get("deadline_to")
        if deadline_from is not None and deadline_to is not None and deadline_from > deadline_to:
            raise ValidationError(
                "Deadline end must not be before deadline start.",
                field_name="deadline_to",
            )


class PublicCompetitionTimeNodeSchema(Schema):
    id = fields.Integer(required=True)
    snapshot_id = fields.Function(lambda node: node.id)
    logical_node_key = fields.String(allow_none=True)
    node_revision = fields.Integer()
    node_type = fields.String(required=True)
    occurs_at = UtcDateTime(allow_none=True)
    starts_at = UtcDateTime(allow_none=True)
    due_at = UtcDateTime(allow_none=True)
    description = fields.String(allow_none=True)
    prominence = fields.String()
    stage_id = fields.Integer(allow_none=True)
    stage_label = fields.Function(lambda node: node.stage.label if node.stage else None)
    stage_order = fields.Function(lambda node: node.stage.stage_order if node.stage else None)
    stage_type = fields.Function(lambda node: node.stage.stage_type if node.stage else None)


class PublicCompetitionSummarySchema(Schema):
    id = fields.Integer(required=True)
    revision_id = fields.Function(lambda competition: competition.published_revision_id)
    title = fields.Function(lambda competition: _revision_value(competition, "title"))
    short_title = fields.Function(lambda competition: _revision_value(competition, "short_title"))
    category = fields.Function(lambda competition: _revision_value(competition, "category"))
    organizer = fields.Function(lambda competition: _revision_value(competition, "organizer"))
    status = fields.Function(lambda competition: competition.status.value)
    source_name = fields.Function(lambda competition: _revision_value(competition, "source_name"))
    source_url = fields.Function(lambda competition: _revision_value(competition, "source_url"))
    official_url = fields.Function(lambda competition: _revision_value(competition, "official_url"))
    content_updated_at = fields.Function(
        lambda competition: (
            competition.published_revision.published_at.isoformat()
            if competition.published_revision and competition.published_revision.published_at
            else None
        )
    )
    tags = fields.Method("serialize_tags")
    participant_forms = fields.Function(
        lambda competition: _revision_value(competition, "participant_forms", []) or []
    )
    suitable_majors = fields.Function(
        lambda competition: _revision_value(competition, "suitable_majors", []) or []
    )
    suitable_grades = fields.Function(
        lambda competition: _revision_value(competition, "suitable_grades", []) or []
    )
    major_scope = fields.Function(lambda competition: _revision_value(competition, "major_scope"))
    grade_scope = fields.Function(lambda competition: _revision_value(competition, "grade_scope"))
    value_notes = fields.Function(lambda competition: _revision_value(competition, "value_notes"))
    next_node = fields.Method("serialize_next_node")
    is_favorited = fields.Constant(False)
    is_subscribed = fields.Constant(False)

    def serialize_tags(self, competition):
        return competition_tag_names(competition)

    def serialize_next_node(self, competition):
        node = next_time_node(competition)
        return public_competition_time_node_schema.dump(node) if node is not None else None


class PublicCompetitionDetailSchema(PublicCompetitionSummarySchema):
    host = fields.Function(lambda competition: _revision_value(competition, "host"))
    attachment_url = fields.Function(
        lambda competition: _revision_value(competition, "attachment_url")
    )
    summary = fields.Function(lambda competition: _revision_value(competition, "summary"))
    detail = fields.Function(lambda competition: _revision_value(competition, "detail"))
    eligibility = fields.Function(lambda competition: _revision_value(competition, "eligibility"))
    registration_applicability = fields.Function(
        lambda competition: _revision_value(competition, "registration_applicability")
    )
    team_size = fields.Function(lambda competition: _revision_value(competition, "team_size"))
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


def _revision_value(competition, field_name: str, default=None):
    revision = competition.published_revision
    return getattr(revision, field_name, default) if revision is not None else default
