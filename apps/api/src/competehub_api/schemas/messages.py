from __future__ import annotations

from marshmallow import Schema, fields, validate

from competehub_api.schemas.common import UtcDateTime

MESSAGE_TYPES = (
    "reminder_due",
    "competition_time_changed",
    "competition_cancelled",
    "competition_offline",
)


class MessageCenterQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    read_status = fields.String(
        load_default="all",
        validate=validate.OneOf(("all", "unread")),
    )
    message_type = fields.String(validate=validate.OneOf(MESSAGE_TYPES))


class MessageTargetSnapshotSchema(Schema):
    competition_id = fields.Integer(required=True)
    competition_title = fields.String(required=True)
    node_type = fields.String(allow_none=True)
    node_occurs_at = fields.String(allow_none=True)
    reason_summary = fields.String(allow_none=True)


class MessageItemSchema(Schema):
    id = fields.Integer(required=True)
    message_type = fields.String(required=True)
    title_snapshot = fields.String(required=True)
    body_snapshot = fields.String(allow_none=True)
    target_snapshot = fields.Nested(MessageTargetSnapshotSchema(), required=True)
    event_occurred_at = UtcDateTime(required=True)
    created_at = UtcDateTime(required=True)
    retained_until = UtcDateTime(required=True)
    is_read = fields.Boolean(required=True)
    read_at = UtcDateTime(allow_none=True)
    target_available = fields.Boolean(required=True)
    target_url = fields.String(allow_none=True)


class MessagePageSchema(Schema):
    items = fields.List(fields.Nested(MessageItemSchema()), required=True)
    pagination = fields.Method("serialize_pagination")

    def serialize_pagination(self, page):
        return {
            "page": page.page,
            "page_size": page.page_size,
            "total": page.total,
        }


message_center_query_schema = MessageCenterQuerySchema()
message_item_schema = MessageItemSchema()
message_page_schema = MessagePageSchema()
