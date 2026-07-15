from __future__ import annotations

import re
import unicodedata

from marshmallow import RAISE, Schema, ValidationError, fields, validate, validates_schema

from competehub_api.schemas.common import NonBlankString, StrictBoolean, UtcDateTime
from competehub_api.seeds.recommendation_rules import CONTROLLED_RECOMMENDATION_RULE_CODES

RULE_TEMPLATE_FIELDS = {
    "major_match": {"major"},
    "grade_match": {"grade"},
    "interest_match": {"interest_tag"},
    "deadline_urgency": {"deadline_date", "days_remaining"},
    "general_fallback": set(),
}
OVERLAP_RULE_CODES = {"major_match", "grade_match", "interest_match"}
PLACEHOLDER_PATTERN = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


class RecommendationRuleInputSchema(Schema):
    class Meta:
        unknown = RAISE

    code = fields.String(
        required=True,
        validate=validate.OneOf(CONTROLLED_RECOMMENDATION_RULE_CODES),
    )
    name = NonBlankString(required=True, validate=validate.Length(max=120))
    weight = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=1, max=100),
    )
    conditions = fields.Dict(required=True)
    reason_template = NonBlankString(required=True, validate=validate.Length(max=200))
    enabled = StrictBoolean(required=True)

    @validates_schema
    def validate_controlled_rule_contract(self, data, **kwargs):
        code = data.get("code")
        conditions = data.get("conditions")
        template = data.get("reason_template")
        if code is None or conditions is None or template is None:
            return

        _validate_conditions(code, conditions)
        _validate_reason_template(code, template)


class RecommendationRuleSetCreateSchema(Schema):
    class Meta:
        unknown = RAISE

    source_rule_set_id = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=1),
    )


class RecommendationRuleSetUpdateSchema(Schema):
    class Meta:
        unknown = RAISE

    rules = fields.List(
        fields.Nested(RecommendationRuleInputSchema()),
        required=True,
        validate=validate.Length(max=len(CONTROLLED_RECOMMENDATION_RULE_CODES)),
    )


class RecommendationRuleSetReviewSchema(Schema):
    class Meta:
        unknown = RAISE

    action = fields.String(required=True, validate=validate.OneOf(["approve", "reject", "return"]))
    comment = NonBlankString(required=True)


class SyntheticProfileSchema(Schema):
    class Meta:
        unknown = RAISE

    college = NonBlankString(required=True, validate=validate.Length(max=120))
    major = NonBlankString(required=True, validate=validate.Length(max=120))
    grade = NonBlankString(required=True, validate=validate.Length(max=40))
    interest_tags = fields.List(
        NonBlankString(),
        required=True,
        validate=validate.Length(min=1, max=10),
    )

    @validates_schema
    def validate_unique_interest_tags(self, data, **kwargs):
        tags = data.get("interest_tags", [])
        if len(tags) != len(set(tags)):
            raise ValidationError({"interest_tags": ["Interest tags must be unique."]})


class RecommendationRuleSetPreviewSchema(Schema):
    class Meta:
        unknown = RAISE

    scenario = fields.String(
        required=True,
        validate=validate.OneOf(["personalized", "general"]),
    )
    synthetic_profile = fields.Nested(SyntheticProfileSchema())
    competition_ids = fields.List(
        fields.Integer(strict=True, validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=20),
    )

    @validates_schema
    def validate_scenario_profile_contract(self, data, **kwargs):
        has_profile = "synthetic_profile" in data
        if data.get("scenario") == "personalized" and not has_profile:
            raise ValidationError(
                {"synthetic_profile": ["A synthetic profile is required for personalized preview."]}
            )
        if data.get("scenario") == "general" and has_profile:
            raise ValidationError(
                {"synthetic_profile": ["General preview must not include a synthetic profile."]}
            )


class GovernanceActorSchema(Schema):
    id = fields.Integer(required=True)
    display_name = fields.String(allow_none=True)


class RecommendationRuleSetReadSchema(Schema):
    rule_set_id = fields.Integer(required=True)
    version = fields.Integer(required=True)
    status = fields.String(required=True)
    created_by = fields.Nested(GovernanceActorSchema(), allow_none=True)
    submitted_by = fields.Nested(GovernanceActorSchema(), allow_none=True)
    reviewed_by = fields.Nested(GovernanceActorSchema(), allow_none=True)
    created_at = UtcDateTime(allow_none=True)
    submitted_at = UtcDateTime(allow_none=True)
    decided_at = UtcDateTime(allow_none=True)
    activated_at = UtcDateTime(allow_none=True)
    retired_at = UtcDateTime(allow_none=True)
    review_comment = fields.String(allow_none=True)
    terminal_review_status = fields.String(allow_none=True)
    cloned_from_rule_set_id = fields.Integer(allow_none=True)
    cloned_from_version = fields.Integer(allow_none=True)
    base_rule_set_id = fields.Integer(allow_none=True)
    base_version = fields.Integer(allow_none=True)
    active_rule_set_id = fields.Integer(allow_none=True)
    active_version = fields.Integer(allow_none=True)
    is_stale = fields.Boolean(required=True)
    difference_snapshot = fields.Dict(allow_none=True)
    impact_summary = fields.Dict(allow_none=True)
    rules = fields.List(fields.Nested(RecommendationRuleInputSchema()), required=True)


def _validate_conditions(code: str, conditions: dict) -> None:
    if code in OVERLAP_RULE_CODES:
        if conditions != {"operator": "overlap"}:
            raise ValidationError(
                {"conditions": ["Conditions do not match the controlled rule code."]}
            )
        return
    if code == "general_fallback":
        if conditions != {"operator": "always"}:
            raise ValidationError(
                {"conditions": ["Conditions do not match the controlled rule code."]}
            )
        return
    if set(conditions) != {"operator", "min_days", "max_days"}:
        raise ValidationError({"conditions": ["Conditions do not match the controlled rule code."]})
    min_days = conditions.get("min_days")
    max_days = conditions.get("max_days")
    if (
        conditions.get("operator") != "within_days"
        or type(min_days) is not int
        or min_days != 0
        or type(max_days) is not int
        or max_days < 0
    ):
        raise ValidationError({"conditions": ["Conditions do not match the controlled rule code."]})


def _validate_reason_template(code: str, template: str) -> None:
    if any(unicodedata.category(character) == "Cc" for character in template):
        raise ValidationError(
            {"reason_template": ["Reason template must be single-line plain text."]}
        )
    placeholders = PLACEHOLDER_PATTERN.findall(template)
    text_without_placeholders = PLACEHOLDER_PATTERN.sub("", template)
    if "{" in text_without_placeholders or "}" in text_without_placeholders:
        raise ValidationError(
            {"reason_template": ["Reason template contains an invalid placeholder."]}
        )
    unknown_placeholders = sorted(set(placeholders) - RULE_TEMPLATE_FIELDS[code])
    if unknown_placeholders:
        raise ValidationError(
            {"reason_template": [f"Unsupported placeholders: {', '.join(unknown_placeholders)}."]}
        )


recommendation_rule_input_schema = RecommendationRuleInputSchema()
recommendation_rule_set_create_schema = RecommendationRuleSetCreateSchema()
recommendation_rule_set_update_schema = RecommendationRuleSetUpdateSchema()
recommendation_rule_set_review_schema = RecommendationRuleSetReviewSchema()
recommendation_rule_set_preview_schema = RecommendationRuleSetPreviewSchema()
recommendation_rule_set_read_schema = RecommendationRuleSetReadSchema()
