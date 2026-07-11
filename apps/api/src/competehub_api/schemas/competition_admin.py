from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, post_load, validate, validates_schema

from competehub_api.models.enums import (
    CompetitionRevisionStatus,
    CompetitionStatus,
    ParticipantForm,
)
from competehub_api.schemas.common import NonBlankString, ProductDateTime


def _optional_text():
    return NonBlankString(allow_none=True)


def _string_list():
    return fields.List(NonBlankString(), allow_none=True)


def _http_url(**kwargs):
    return fields.Url(schemes={"http", "https"}, **kwargs)


CORE_NODE_TYPES = {
    "registration_start",
    "registration_deadline",
    "submission_deadline",
    "competition_start",
    "competition_end",
    "defense_or_review",
    "result_announcement",
    "other",
}
APPLICABILITY_SCOPES = {"all", "selected", "unknown"}
REGISTRATION_APPLICABILITY = {"applicable", "not_applicable", "unknown"}
PRIMARY_NODE_TYPES = {
    "registration_deadline",
    "submission_deadline",
    "competition_start",
}


class CompetitionTimeNodeSchema(Schema):
    id = fields.Integer(dump_only=True)
    node_type = NonBlankString(required=True)
    starts_at = ProductDateTime(allow_none=True)
    due_at = ProductDateTime(allow_none=True)
    description = _optional_text()

    @validates_schema
    def validate_has_time(self, data, **kwargs):
        if data.get("starts_at") is None and data.get("due_at") is None:
            raise ValidationError("A start or due time is required.")


class CompetitionTagSchema(Schema):
    code = NonBlankString(required=True)
    name = NonBlankString(required=True)
    tag_type = NonBlankString(required=True)
    description = _optional_text()


class CompetitionReviewSchema(Schema):
    action = fields.String(
        required=True,
        validate=validate.OneOf(["approve", "reject", "return"]),
    )
    comment = NonBlankString(required=True)


class CompetitionStatusSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf([status.value for status in CompetitionStatus]),
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
    time_nodes = fields.List(fields.Nested(CompetitionTimeNodeSchema()))
    tags = fields.Method("serialize_tags")

    def serialize_tags(self, competition):
        tags = [link.tag for link in competition.tag_links if link.tag is not None]
        return CompetitionTagSchema().dump(tags, many=True)


class CompetitionSeriesCreateSchema(Schema):
    canonical_name = NonBlankString(required=True)


class CompetitionSeriesSchema(Schema):
    id = fields.Integer(required=True)
    canonical_name = fields.String(required=True)


class RevisionTimeNodeSchema(Schema):
    id = fields.Integer(dump_only=True)
    logical_node_key = NonBlankString(required=True)
    node_revision = fields.Integer(dump_only=True)
    node_type = fields.String(required=True, validate=validate.OneOf(sorted(CORE_NODE_TYPES)))
    occurs_at = ProductDateTime(required=True)
    description = _optional_text()
    prominence = fields.String(validate=validate.OneOf(["primary", "secondary"]))
    prominence_override_reason = _optional_text()

    @validates_schema
    def validate_other_description(self, data, **kwargs):
        if data.get("node_type") == "other" and not data.get("description"):
            raise ValidationError(
                "Other time nodes require a description.", field_name="description"
            )

    @post_load
    def apply_prominence_default(self, data, **kwargs):
        default = "primary" if data["node_type"] in PRIMARY_NODE_TYPES else "secondary"
        supplied = data.get("prominence")
        if supplied is None:
            data["prominence"] = default
        elif supplied != default and not data.get("prominence_override_reason"):
            raise ValidationError(
                "A prominence override requires a reason.",
                field_name="prominence_override_reason",
            )
        return data


class CompetitionStageSchema(Schema):
    id = fields.Integer(dump_only=True)
    stage_key = NonBlankString(required=True)
    stage_type = NonBlankString(required=True)
    label = NonBlankString(required=True)
    order = fields.Integer(attribute="stage_order", required=True, validate=validate.Range(min=1))
    time_nodes = fields.List(fields.Nested(RevisionTimeNodeSchema()), required=True)

    @validates_schema
    def validate_chronology(self, data, **kwargs):
        by_type = {node["node_type"]: node["occurs_at"] for node in data.get("time_nodes", [])}
        for start_type, end_type in (
            ("registration_start", "registration_deadline"),
            ("competition_start", "competition_end"),
        ):
            if start_type in by_type and end_type in by_type:
                if by_type[start_type] > by_type[end_type]:
                    raise ValidationError(
                        f"{start_type} must not occur after {end_type}.",
                        field_name="time_nodes",
                    )


class CompetitionRevisionFieldsSchema(Schema):
    title = _optional_text()
    short_title = _optional_text()
    category = _optional_text()
    organizer = _optional_text()
    host = _optional_text()
    source_name = _optional_text()
    source_url = _http_url(allow_none=True)
    official_url = _http_url(allow_none=True)
    attachment_url = _http_url(allow_none=True)
    summary = _optional_text()
    detail = _optional_text()
    eligibility = _optional_text()
    registration_applicability = fields.String(
        allow_none=True,
        validate=validate.OneOf(sorted(REGISTRATION_APPLICABILITY)),
    )
    team_size = _optional_text()
    participant_forms = fields.List(
        fields.String(validate=validate.OneOf([form.value for form in ParticipantForm])),
        allow_none=True,
    )
    suitable_majors = _string_list()
    suitable_grades = _string_list()
    major_scope = fields.String(
        allow_none=True,
        validate=validate.OneOf(sorted(APPLICABILITY_SCOPES)),
    )
    grade_scope = fields.String(
        allow_none=True,
        validate=validate.OneOf(sorted(APPLICABILITY_SCOPES)),
    )
    value_notes = _optional_text()
    stages = fields.List(fields.Nested(CompetitionStageSchema()), allow_none=True)
    tags = fields.List(fields.Nested(CompetitionTagSchema()), allow_none=True)

    @validates_schema
    def validate_unique_stage_and_node_keys(self, data, **kwargs):
        tags = data.get("tags")
        if tags is not None and len({tag["code"] for tag in tags}) != len(tags):
            raise ValidationError("Tag codes must be unique.", field_name="tags")
        for scope_field, values_field in (
            ("major_scope", "suitable_majors"),
            ("grade_scope", "suitable_grades"),
        ):
            if data.get(scope_field) == "selected" and not data.get(values_field):
                raise ValidationError(
                    "Selected scope requires at least one controlled value.",
                    field_name=values_field,
                )
            values = data.get(values_field)
            if values is not None and len(values) != len(set(values)):
                raise ValidationError(
                    "Controlled scope values must be unique.",
                    field_name=values_field,
                )
        participant_forms = data.get("participant_forms")
        if participant_forms is not None and len(participant_forms) != len(set(participant_forms)):
            raise ValidationError(
                "Participant forms must be unique.", field_name="participant_forms"
            )
        stages = data.get("stages")
        if stages is None:
            return
        stage_keys = [stage["stage_key"] for stage in stages]
        stage_orders = [stage["stage_order"] for stage in stages]
        node_keys = [
            node["logical_node_key"] for stage in stages for node in stage.get("time_nodes", [])
        ]
        if len(stage_keys) != len(set(stage_keys)):
            raise ValidationError("Stage keys must be unique.", field_name="stages")
        if len(stage_orders) != len(set(stage_orders)):
            raise ValidationError("Stage orders must be unique.", field_name="stages")
        if len(node_keys) != len(set(node_keys)):
            raise ValidationError("Logical node keys must be unique.", field_name="stages")


class EditionCreateSchema(CompetitionRevisionFieldsSchema):
    series_id = fields.Integer(required=True)
    edition_label = NonBlankString(required=True)
    title = NonBlankString(required=True)
    source_name = NonBlankString(required=True)
    source_url = _http_url(required=True)


class CompetitionRevisionUpdateSchema(CompetitionRevisionFieldsSchema):
    @validates_schema
    def validate_has_updates(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one editable field is required.")


class CompetitionRevisionSchema(Schema):
    id = fields.Integer(required=True)
    competition_id = fields.Integer(required=True)
    revision_number = fields.Integer(required=True)
    base_revision_id = fields.Integer(allow_none=True)
    revision_status = fields.Function(lambda revision: revision.revision_status.value)
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
    registration_applicability = fields.String(allow_none=True)
    team_size = fields.String(allow_none=True)
    participant_forms = fields.List(fields.String())
    suitable_majors = fields.List(fields.String(), allow_none=True)
    suitable_grades = fields.List(fields.String(), allow_none=True)
    major_scope = fields.String(allow_none=True)
    grade_scope = fields.String(allow_none=True)
    value_notes = fields.String(allow_none=True)
    created_by_id = fields.Integer(required=True)
    submitted_by_id = fields.Integer(allow_none=True)
    submitted_at = fields.DateTime(allow_none=True)
    decided_at = fields.DateTime(allow_none=True)
    published_at = fields.DateTime(allow_none=True)
    stages = fields.List(fields.Nested(CompetitionStageSchema()))
    tags = fields.Method("serialize_tags")

    def serialize_tags(self, revision):
        tags = [link.tag for link in revision.tag_links if link.tag is not None]
        return CompetitionTagSchema().dump(tags, many=True)


class EditionWorkspaceSchema(Schema):
    id = fields.Integer(required=True)
    series_id = fields.Integer(required=True)
    edition_label = fields.String(required=True)
    lifecycle_status = fields.Function(
        lambda edition: (
            edition.status.value
            if edition.status in {CompetitionStatus.UNPUBLISHED, CompetitionStatus.PUBLISHED}
            else "unpublished"
        )
    )
    published_revision_id = fields.Integer(allow_none=True)
    revision = fields.Method("serialize_revision")
    active_revision = fields.Method("serialize_revision")

    def serialize_revision(self, edition):
        active = next(
            (
                revision
                for revision in reversed(edition.revisions)
                if revision.revision_status
                in {
                    CompetitionRevisionStatus.DRAFT,
                    CompetitionRevisionStatus.PENDING_REVIEW,
                }
            ),
            edition.published_revision,
        )
        return competition_revision_schema.dump(active) if active is not None else None


competition_review_schema = CompetitionReviewSchema()
competition_status_schema = CompetitionStatusSchema()
competition_schema = CompetitionSchema()
competition_series_create_schema = CompetitionSeriesCreateSchema()
competition_series_schema = CompetitionSeriesSchema()
edition_create_schema = EditionCreateSchema()
competition_revision_update_schema = CompetitionRevisionUpdateSchema()
competition_revision_schema = CompetitionRevisionSchema()
edition_workspace_schema = EditionWorkspaceSchema()
