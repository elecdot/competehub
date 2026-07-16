from __future__ import annotations

from datetime import date

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from competehub_api.schemas.common import UtcDateTime

CALENDAR_DATE_MIN = date(1, 1, 2)
CALENDAR_DATE_MAX = date(9999, 12, 30)


class CalendarQuerySchema(Schema):
    date_from = fields.Date(
        required=True,
        data_key="from",
        validate=validate.Range(min=CALENDAR_DATE_MIN, max=CALENDAR_DATE_MAX),
    )
    date_to = fields.Date(
        required=True,
        data_key="to",
        validate=validate.Range(min=CALENDAR_DATE_MIN, max=CALENDAR_DATE_MAX),
    )
    view = fields.String(
        required=True,
        validate=validate.OneOf(["month", "week", "list"]),
    )

    @validates_schema
    def validate_range(self, data, **kwargs):
        if data.get("date_from") and data.get("date_to"):
            if data["date_from"] > data["date_to"]:
                raise ValidationError(
                    "Calendar end must not be before calendar start.",
                    field_name="to",
                )


class CalendarRangeSchema(Schema):
    date_from = fields.Date(attribute="from", data_key="from")
    date_to = fields.Date(attribute="to", data_key="to")
    view = fields.String()
    time_zone = fields.String()


class CalendarItemSchema(Schema):
    competition_id = fields.Integer()
    competition_title = fields.String()
    detail_url = fields.String(allow_none=True)
    lifecycle_status = fields.String()
    target_available = fields.Boolean()
    stage_id = fields.Integer(allow_none=True)
    stage_label = fields.String(allow_none=True)
    stage_order = fields.Integer(allow_none=True)
    stage_type = fields.String(allow_none=True)
    is_current_stage = fields.Boolean()
    node_snapshot_id = fields.Integer()
    logical_node_key = fields.String(allow_none=True)
    node_revision = fields.Integer()
    node_type = fields.String()
    description = fields.String(allow_none=True)
    occurs_at = UtcDateTime()
    prominence = fields.String()
    pair_kind = fields.String(allow_none=True)
    pair_role = fields.String(allow_none=True)


class CalendarPayloadSchema(Schema):
    range = fields.Nested(CalendarRangeSchema())
    items = fields.List(fields.Nested(CalendarItemSchema()))


calendar_query_schema = CalendarQuerySchema()
calendar_payload_schema = CalendarPayloadSchema()
